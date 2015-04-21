"""
Tests for Discussion API views
"""
from datetime import datetime
import json

import mock
from pytz import UTC

from django.core.urlresolvers import reverse

from student.tests.factories import CourseEnrollmentFactory, UserFactory
from util.testing import UrlResetMixin
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


class CourseTopicsViewTest(UrlResetMixin, ModuleStoreTestCase):
    """Tests for CourseTopicsView"""

    @mock.patch.dict("django.conf.settings.FEATURES", {"ENABLE_DISCUSSION_SERVICE": True})
    def setUp(self):
        super(CourseTopicsViewTest, self).setUp()
        self.maxDiff = None  # pylint: disable=invalid-name
        self.course = CourseFactory.create(
            org="x",
            course="y",
            run="z",
            start=datetime.now(UTC),
            discussion_topics={"Test Topic": {"id": "test_topic"}}
        )
        self.password = "password"
        self.user = UserFactory.create(password=self.password)
        CourseEnrollmentFactory.create(user=self.user, course_id=self.course.id)
        self.url = reverse("course_topics", kwargs={"course_id": unicode(self.course.id)})
        self.client.login(username=self.user.username, password=self.password)

    def assert_response_correct(self, response, expected_status, expected_content):
        """
        Assert that the response has the given status code and parsed content
        """
        self.assertEqual(response.status_code, expected_status)
        parsed_content = json.loads(response.content)
        self.assertEqual(parsed_content, expected_content)

    def test_not_authenticated(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assert_response_correct(
            response,
            401,
            {"developer_message": "Request must be authenticated"}
        )

    def test_non_existent_course(self):
        response = self.client.get(
            reverse("course_topics", kwargs={"course_id": "non/existent/course"})
        )
        self.assert_response_correct(
            response,
            404,
            {"developer_message": "Course not found"}
        )

    def test_not_enrolled(self):
        unenrolled_user = UserFactory.create(password=self.password)
        self.client.login(username=unenrolled_user.username, password=self.password)
        response = self.client.get(self.url)
        self.assert_response_correct(
            response,
            404,
            {"developer_message": "Course not found"}
        )

    def test_get(self):
        response = self.client.get(self.url)
        self.assert_response_correct(
            response,
            200,
            {
                "courseware_topics": [],
                "non_courseware_topics": [{
                    "id": "test_topic",
                    "name": "Test Topic",
                    "thread_list_url": (
                        "http://testserver/courses/x/y/z/discussion/forum?"
                        "commentable_id=test_topic"
                    ),
                    "children": []
                }],
            }
        )

    def test_methods_not_allowed(self):
        for method in ["post", "put", "delete"]:  # TODO add patch when we upgrade django
            func = getattr(self.client, method)
            response = func(self.url)
            self.assert_response_correct(
                response,
                405,
                {"developer_message": "Only GET, OPTIONS, and HEAD are allowed"}
            )
