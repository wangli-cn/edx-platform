""" Commerce views. """
import logging

from django.conf import settings
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_406_NOT_ACCEPTABLE, HTTP_202_ACCEPTED, HTTP_409_CONFLICT
from rest_framework.views import APIView
from xmodule.modulestore.django import modulestore

from commerce.api import EcommerceAPI
from commerce.constants import OrderStatus, Messages
from commerce.exceptions import ApiError, InvalidConfigurationError
from commerce.http import DetailResponse, InternalRequestErrorResponse
from course_modes.models import CourseMode
from courseware import courses
from edxmako.shortcuts import render_to_response as mako_render_to_response
from enrollment.api import add_enrollment
from microsite_configuration import microsite
from student.models import CourseEnrollment
from openedx.core.lib.api.authentication import SessionAuthenticationAllowInactiveUser
from util.date_utils import get_default_time_display
from util.json_request import JsonResponse


log = logging.getLogger(__name__)


class OrdersView(APIView):
    """ Creates an order with a course seat and enrolls users. """

    # LMS utilizes User.user_is_active to indicate email verification, not whether an account is active. Sigh!
    authentication_classes = (SessionAuthenticationAllowInactiveUser,)
    permission_classes = (IsAuthenticated,)

    def _is_data_valid(self, request):
        """
        Validates the data posted to the view.

        Arguments
            request -- HTTP request

        Returns
            Tuple (data_is_valid, course_key, error_msg)
        """
        course_id = request.DATA.get('course_id')

        if not course_id:
            return False, None, u'Field course_id is missing.'

        try:
            course_key = CourseKey.from_string(course_id)
            courses.get_course(course_key)
        except (InvalidKeyError, ValueError)as ex:
            log.exception(u'Unable to locate course matching %s.', course_id)
            return False, None, ex.message

        return True, course_key, None

    def _enroll(self, course_key, user):
        """ Enroll the user in the course. """
        add_enrollment(user.username, unicode(course_key))

    def post(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Attempt to create the order and enroll the user.
        """
        user = request.user
        valid, course_key, error = self._is_data_valid(request)
        if not valid:
            return DetailResponse(error, status=HTTP_406_NOT_ACCEPTABLE)

        # Don't do anything if an enrollment already exists
        course_id = unicode(course_key)
        enrollment = CourseEnrollment.get_enrollment(user, course_key)
        if enrollment and enrollment.is_active:
            msg = Messages.ENROLLMENT_EXISTS.format(course_id=course_id, username=user.username)
            return DetailResponse(msg, status=HTTP_409_CONFLICT)

        # If there is no honor course mode, this most likely a Prof-Ed course. Return an error so that the JS
        # redirects to track selection.
        honor_mode = CourseMode.mode_for_course(course_key, CourseMode.HONOR)

        if not honor_mode:
            msg = Messages.NO_HONOR_MODE.format(course_id=course_id)
            return DetailResponse(msg, status=HTTP_406_NOT_ACCEPTABLE)
        elif not honor_mode.sku:
            # If there are no course modes with SKUs, enroll the user without contacting the external API.
            msg = Messages.NO_SKU_ENROLLED.format(enrollment_mode=CourseMode.HONOR, course_id=course_id,
                                                  username=user.username)
            log.debug(msg)
            self._enroll(course_key, user)
            return DetailResponse(msg)

        # Setup the API and report any errors if settings are not valid.
        try:
            api = EcommerceAPI()
        except InvalidConfigurationError:
            self._enroll(course_key, user)
            msg = Messages.NO_ECOM_API.format(username=user.username, course_id=unicode(course_key))
            log.debug(msg)
            return DetailResponse(msg)

        # Make the API call
        try:
            order_number, order_status, _body = api.create_order(user, honor_mode.sku)
            if order_status == OrderStatus.COMPLETE:
                msg = Messages.ORDER_COMPLETED.format(order_number=order_number)
                log.debug(msg)
                return DetailResponse(msg)
            else:
                # TODO Before this functionality is fully rolled-out, this branch should be updated to NOT enroll the
                # user. Enrollments must be initiated by the E-Commerce API only.
                self._enroll(course_key, user)
                msg = u'Order %(order_number)s was received with %(status)s status. Expected %(complete_status)s. ' \
                      u'User %(username)s was enrolled in %(course_id)s by LMS.'
                msg_kwargs = {
                    'order_number': order_number,
                    'status': order_status,
                    'complete_status': OrderStatus.COMPLETE,
                    'username': user.username,
                    'course_id': course_id,
                }
                log.error(msg, msg_kwargs)

                msg = Messages.ORDER_INCOMPLETE_ENROLLED.format(order_number=order_number)
                return DetailResponse(msg, status=HTTP_202_ACCEPTED)
        except ApiError as err:
            # The API will handle logging of the error.
            return InternalRequestErrorResponse(err.message)


@cache_page(1800)
def checkout_cancel(_request):
    """ Checkout/payment cancellation view. """
    context = {'payment_support_email': microsite.get_value('payment_support_email', settings.PAYMENT_SUPPORT_EMAIL)}
    return mako_render_to_response("commerce/checkout_cancel.html", context)


class CheckoutReceiptView(TemplateView):
    template_name = 'commerce/checkout_receipt.html'

    def get_context_data(self, **kwargs):
        data = super(CheckoutReceiptView, self).get_context_data(**kwargs)
        basket_id = self.request.GET.get('basket_id')

        order = None
        course_id = None
        course_name = None

        if basket_id:
            _order_id, _order_status, order = EcommerceAPI().get_basket_order(self.request.user, basket_id)

            # Format the order placement date
            order['date_placed'] = get_default_time_display(order['date_placed'])

            # Get the course_id
            for line in order['lines']:
                attributes = line['product']['attribute_values']
                for attribute in attributes:
                    if attribute['name'] == 'course_key':
                        course_id = attribute['value']

            # Get the course name
            course_key = CourseKey.from_string(course_id)
            course = modulestore().get_course(course_key)
            course_name = course.display_name

        data.update({
            'order': order,
            'course_id': course_id,
            'course_name': course_name,
            'platform_name': settings.PLATFORM_NAME
        })
        return data


class BasketOrderView(APIView):
    """ Retrieve the order associated with a basket. """

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        _order_id, _order_status, order = EcommerceAPI().get_basket_order(request.user, kwargs['basket_id'])
        return JsonResponse(order)
