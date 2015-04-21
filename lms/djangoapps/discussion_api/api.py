"""
Discussion API internal interface
"""
from collections import defaultdict
from urllib import urlencode
from urlparse import urlunsplit

from django.core.urlresolvers import reverse

from django_comment_client.utils import get_accessible_discussion_modules


def get_course_topics(course, user, build_absolute_uri):
    """
    Return the course topic listing for the given course and user.

    Parameters:

    course: The course to get topics for
    user: The requesting user, for access control
    build_absolute_uri: a function that takes a relative URI and returns an
        absolute URI

    Returns:

    A course topic listing dictionary with the following items:

    courseware_topics: The list of topic trees for courseware-linked topics
    non_courseware_toipcs: The list of topic tree that are not courseware-linked

    Each topic tree has the following items:

    id: The id of the discussion topic (null for a category that only has
        children but cannot contain threads itself)
    name: The display name of the discussion topic
    thread_list_url: A URL to retrieve the threads that belong to the topic
    children: A list of child subtrees
    """

    # TODO: This is temporary until the discussion_api thread list view is implemented
    thread_list_path = reverse(
        "django_comment_client.forum.views.forum_form_discussion",
        kwargs={"course_id": unicode(course.id)}
    )

    def get_thread_list_url_with_query(query):
        """
        Given the appropriate filter query part, return the full thread list URL
        """
        return build_absolute_uri(urlunsplit((None, None, thread_list_path, query, None)))

    def get_multi_topic_url(topic_ids):
        """
        Given a list of topic ids, return the URL to retrieve the combined list
        of threads for those topics
        """
        return get_thread_list_url_with_query(
            urlencode({"commentable_ids": ",".join(sorted(topic_ids))})
        )

    def get_single_topic_url(topic_id):
        """
        Given a single topic id, return the URL to retrieve the list of threads
        for that topic
        """
        return get_thread_list_url_with_query(urlencode({"commentable_id": topic_id}))

    def get_module_sort_key(module):
        """
        Get the sort key for the module (falling back to the discussion_target
        setting if absent)
        """
        return module.sort_key or module.discussion_target

    discussion_modules = get_accessible_discussion_modules(course, user)
    modules_by_category = defaultdict(list)
    for module in discussion_modules:
        modules_by_category[module.discussion_category].append(module)
    courseware_topics = [
        {
            "id": None,
            "name": category,
            "thread_list_url": get_multi_topic_url(
                module.discussion_id for module in modules_by_category[category]
            ),
            "children": [
                {
                    "id": module.discussion_id,
                    "name": module.discussion_target,
                    "thread_list_url": get_single_topic_url(module.discussion_id),
                    "children": [],
                }
                for module in sorted(modules_by_category[category], key=get_module_sort_key)
            ],
        }
        for category in sorted(modules_by_category.keys())
    ]

    non_courseware_topics = [
        {
            "id": entry["id"],
            "name": name,
            "thread_list_url": get_single_topic_url(entry["id"]),
            "children": [],
        }
        for name, entry in sorted(
            course.discussion_topics.items(),
            key=lambda item: item[1].get("sort_key", item[0])
        )
    ]

    return {
        "courseware_topics": courseware_topics,
        "non_courseware_topics": non_courseware_topics,
    }
