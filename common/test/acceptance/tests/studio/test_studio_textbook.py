"""
Acceptance tests for Studio related to the textbook.
"""
from acceptance.tests.studio.base_studio_test import StudioCourseTest
from ...pages.studio.textbooks import TextbooksPage

class TextbookTest(StudioCourseTest):

    def setUp(self):
        """
        Install a course with no content using a fixture.
        """
        super(TextbookTest, self).setUp(is_staff=True)
        self.textbook_page = TextbooksPage(self.browser, self.course_info['org'], self.course_info['number'], self.course_info['run'])
        self.textbook_page.visit()

    def test_create_first_book_message(self):
        message = self.textbook_page.get_element_text('.wrapper-content .no-textbook-content')
        self.assertIn("You haven't added any textbooks", message)

    def test_new_textbook_upload(self):
        self.textbook_page.open_add_textbook_form()
        self.textbook_page.upload_pdf_file('textbook.pdf')
        self.textbook_page.set_input_field_value('.edit-textbook #textbook-name-input', 'book 1')
        self.textbook_page.set_input_field_value('.edit-textbook #chapter1-name', 'chapter 1')
        from nose.tools import set_trace; set_trace()

    def test_upload(self):
        self.textbook_page.open_add_textbook_form()
        from nose.tools import set_trace; set_trace()
        print "waqas"
