from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import User, Post, Group, Follow, Comment
from yatube.settings import CACHES

CACHE = {
    'default': {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}


class ProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sarah")
        self.group = Group.objects.create(title="Test group",
                                          slug="testgroup",
                                          description="Тестовая группа")
        self.client_login = Client()
        self.client_login.force_login(self.user)
        self.client_logout = Client()

    def test_profile(self):
        response = self.client_logout.get(reverse("profile", args=[
            self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["post_author"], User)
        self.assertEqual(response.context["post_author"], self.user)

    def test_post_pub_auth(self):
        response = self.client_login.post(reverse("new_post"),
                                          {"group": self.group.pk,
                                           "text": "Приличный текст"},
                                          follow=True)
        self.assertEqual(response.status_code, 200)
        posts = Post.objects.all()
        post = posts.first()
        self.assertEqual(posts.count(), 1)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)

    def test_post_pub_not_auth(self):
        response = self.client_logout.post(reverse("new_post"),
                                           {"group": "",
                                            "text": "Приличный текст"},
                                           follow=True)
        posts = Post.objects.all()
        self.assertEqual(posts.count(), 0)
        new_url = reverse("new_post")
        login_url = reverse("login")
        self.assertRedirects(response, f'{login_url}?next={new_url}')

    def contains(self, url, user, text, group):
        response = self.client_login.get(url)
        if 'page' in response.context:
            test_post = response.context['page'][0]
            self.assertEqual(
                response.context['paginator'].num_pages, 1)
        else:
            test_post = response.context['post']
        self.assertEqual(test_post.author, user)
        self.assertEqual(test_post.group, group)
        self.assertEqual(test_post.text, text)

    @override_settings(CACHES=CACHE)
    def test_pub_place(self):
        text = "Приличный текст"
        post = Post.objects.create(author=self.user, group=self.group,
                                   text=text)
        urls_list = [reverse("index"),
                     reverse("profile", args=[self.user.username]),
                     reverse("post", args=[self.user.username, post.pk])]
        for url in urls_list:
            self.contains(url, self.user, text, self.group)

    @override_settings(CACHES=CACHE)
    def test_post_edit(self):
        post = Post.objects.create(author=self.user, group=self.group,
                                   text="Приличный текст")
        text = "НЕприличный текст"
        group = Group.objects.create(title="groupone",
                                     slug="groupone",
                                     description="группа")

        self.client_login.post(
            reverse("post_edit", args=[self.user.username, post.pk]),
            {"group": group.pk, "text": text}, follow=True)

        self.assertEqual(self.group.posts.count(), 0)
        response = self.client_login.get(reverse("group_posts",
                                                 args=[self.group.slug]))
        self.assertEqual(response.context['paginator'].count, 0)

        urls_list = [reverse("index"),
                     reverse("profile", args=[self.user.username]),
                     reverse("post", args=[self.user.username, post.pk]),
                     reverse("group_posts", args=[group.slug])]
        for url in urls_list:
            self.contains(url, self.user, text, group)

    def test_404_code(self):
        response = self.client_logout.get('/400/ ')
        self.assertEqual(response.status_code, 404)

    @override_settings(CACHES=CACHE)
    def test_image(self):
        img = SimpleUploadedFile(name="test_img.jpg",
                                 content=b"file_content",
                                 content_type="image/jpeg")
        Post.objects.create(author=self.user, text="post with image",
                            image=img)
        post_id = Post.objects.filter(author=self.user).first().pk
        response = self.client_login.get(
            reverse("post", args=[self.user.username, post_id]))
        self.assertContains(response, "<img")

    @override_settings(CACHES=CACHE)
    def test_image_pub(self):
        img = SimpleUploadedFile(name="test_img.jpg",
                                 content=b"file_content",
                                 content_type="image/jpeg")
        Post.objects.create(author=self.user, text="post with image",
                            group=self.group, image=img)
        urls_list = [reverse("index"),
                     reverse("profile", args=[self.user.username]),
                     reverse("group_posts", args=[self.group.slug])]
        for url in urls_list:
            response = self.client_login.get(url)
            self.assertContains(response, "<img")

    def test_pub_not_image(self):
        txt = SimpleUploadedFile(name='test_text.txt',
                                 content=b'abc',
                                 content_type='text/plain')
        response = self.client_login.post(reverse("new_post"),
                                          {'author': self.user,
                                           'text': 'post with image',
                                           'image': txt}, follow=True)
        self.assertFormError(response, "form", "image",
                             errors='Загрузите правильное изображение. Файл, который вы загрузили, поврежден или не является изображением.')

    def test_cache(self):
        text = "Приличный текст"
        text_new = "НЕприличный текст"
        Post.objects.create(author=self.user, group=self.group,
                            text=text)
        response = self.client_login.get(reverse("index"))
        self.assertContains(response, text)
        Post.objects.create(author=self.user, group=self.group,
                            text=text_new)
        response_new = self.client_login.get(reverse("index"))
        self.assertNotContains(response_new, text_new)

    def test_auth_user_can_follow(self):
        author = User.objects.create_user(username="arni")
        response = self.client_login.get(reverse("profile_follow", args=[
            author.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        follow = Follow.objects.all()
        self.assertEqual(follow.count(), 1)
        self.assertEqual(follow.first().author, author)
        self.assertEqual(follow.first().user, self.user)

    def test_auth_user_can_unfollow(self):
        author = User.objects.create_user(username="arni")
        Follow.objects.create(user=self.user, author=author)
        response = self.client_login.get(
            reverse("profile_unfollow", args=[author.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 0)

    def test_user_can_see_follow_pub(self):
        author = User.objects.create_user(username="arni")
        post = Post.objects.create(author=author, group=self.group,
                                   text="test")
        Follow.objects.create(user=self.user, author=author)

        response = self.client_login.get(reverse("follow_index"))
        self.assertEqual(response.status_code, 200)
        self.contains(reverse("follow_index"), author, "test", self.group)

    def test_user_cant_see_unfollow_pub(self):
        author = User.objects.create_user(username="arni")
        post = Post.objects.create(author=author, group=self.group,
                                   text="test")
        self.client_login.force_login(author)
        new_response = self.client_login.get(reverse("follow_index"))
        self.assertEqual(new_response.status_code, 200)
        self.assertNotContains(new_response, post.text)

    def test_no_auth_user_cant_comment(self):
        post = Post.objects.create(author=self.user, group=self.group,
                                   text="test")
        self.client_logout.post(
            reverse("add_comment", args=[self.user, post.pk]),
            {"text": "test"})
        self.assertEqual(Comment.objects.count(), 0)

    def test_auth_user_can_comment(self):
        post = Post.objects.create(author=self.user, group=self.group,
                                   text="test")
        response = self.client_login.post(
            reverse("add_comment", args=[self.user, post.pk]),
            {"text": "test"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.first().post, post)
        self.assertEqual(post.comments.first().text, "test")
        self.assertEqual(post.comments.first().author, self.user)
