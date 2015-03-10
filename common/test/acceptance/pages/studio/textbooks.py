"""
Course Textbooks page.
"""

from .course_page import CoursePage
from path import path
from bok_choy.promise import EmptyPromise

class TextbooksPage(CoursePage):
    """
    Course Textbooks page.
    """

    url_path = "textbooks"

    def is_browser_on_page(self):
        return self.q(css='body.view-textbooks').present

    def open_add_textbook_form(self):
        self.q(css='.nav-item .new-button').click()

    def get_element_text(self, selector):
        return self.q(css=selector)[0].text

    def _is_element_visible(self, selector):
        query = self.q(css=selector)
        return query.present and query.visible

    def set_input_field_value(self, selector, value):
        self.q(css=selector)[0].send_keys(value)

    def upload_pdf_file(self, file_name):
        """
        Uploads a pdf textbook
        """
        # If the pdf upload section has not yet been toggled on, click on the upload pdf button
        test_dir = path(__file__).abspath().dirname().dirname().dirname()
        file_path = test_dir + '/data/uploads/' + file_name

        pdf_upload_toggle = self.q(css=".edit-textbook .action-upload").first
        if pdf_upload_toggle:
            pdf_upload_toggle.click()
        file_input = self.q(css=".upload-dialog input").results[0]
        file_input.send_keys(file_path)
        from nose.tools import set_trace; set_trace()
        self.q(css=".wrapper-modal-window-assetupload .action-upload").first.click()
        EmptyPromise(
            lambda: not self._is_element_visible(".wrapper-modal-window-assetupload"),
            "Upload modal closed"
        ).fulfill()
