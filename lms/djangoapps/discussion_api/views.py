"""
Discussion API views
"""
from django.http import Http404

from rest_framework.authentication import OAuth2Authentication, SessionAuthentication
from rest_framework.exceptions import MethodNotAllowed, NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from opaque_keys.edx.locator import CourseLocator

from courseware.courses import get_course_with_access
from discussion_api.api import get_course_topics


def _make_error_response(status_code, developer_message):
    """
    Return an error response with the given status code and developer
    message
    """
    return Response({"developer_message": developer_message}, status=status_code)


class CourseTopicsView(APIView):
    """
    A read-only endpoint to retrieve the topic listing for a user in a course.

    The course_id in the URL is used to look up a course, and the authenticated
    user is used for access control.

    Response:

    A course topic listing with the following items:

    courseware_topics: The list of topic trees for courseware-linked topics
    non_courseware_toipcs: The list of topic tree that are not courseware-linked

    Each topic tree has the following items:

    id: The id of the discussion topic (null for a category that only has
        children but cannot contain threads itself)
    name: The display name of the discussion topic
    thread_list_url: A URL to retrieve the threads that belong to the topic
    children: A list of child subtrees

    Errors:
    401: if the request is not authenticated
    404: if the course_id does not identify a valid course or if the user does
        not have access to the course (i.e. is not enrolled)
    405: if a method other than OPTIONS, HEAD, or GET is specified
    """
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id):
        course_key = CourseLocator.from_string(course_id)
        course = get_course_with_access(request.user, 'load_forum', course_key)
        return Response(get_course_topics(course, request.user, request.build_absolute_uri))

    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return _make_error_response(401, "Request must be authenticated")
        elif isinstance(exc, Http404):
            return _make_error_response(404, "Course not found")
        elif isinstance(exc, MethodNotAllowed):
            return _make_error_response(405, "Only GET, OPTIONS, and HEAD are allowed")
        else:
            return super(CourseTopicsView, self).handle_exception(exc)
