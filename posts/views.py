from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect

from . import forms
from .models import Post, Group, User, Follow


def index(request):
    post_list = Post.objects.all().select_related("group")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)

    return render(request, "index.html",
                  {"page": page, "paginator": paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    group_post_list = group.posts.all()
    paginator = Paginator(group_post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"group": group, "page": page,
                                          "paginator": paginator})


@login_required
def new_post(request):
    if request.method == 'POST':
        form = forms.PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            new = form.save(commit=False)
            new.author = request.user
            new.save()
            return redirect('index')
        return render(request, 'new.html', {'form': form})
    form = forms.PostForm()
    return render(request, 'new.html', {'form': form})


def profile(request, username):
    user = get_object_or_404(User, username=username)
    user_post_list = user.posts.all()
    paginator = Paginator(user_post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    following = user.following.all()
    return render(request, 'profile.html', {'post_author': user, 'page': page,
                                            'paginator': paginator,
                                            'post_count': paginator.count,
                                            "following": following})


def post_view(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    post_count = post.author.posts.count()
    comments = post.comments.all()
    form = forms.CommentForm(request.POST or None)
    return render(request, 'post.html',
                  {'post': post, 'post_author': post.author,
                   'post_count': post_count, 'comments': comments,
                   'form': form})


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    if post.author != request.user:
        return redirect('post', username=username, post_id=post_id)
    form = forms.PostForm(request.POST or None, files=request.FILES or None,
                          instance=post)
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'new.html',
                  {'form': form, 'username': username, 'post': post})


def page_not_found(request, exception):
    return render(request, "misc/404.html", {"path": request.path}, status=404)


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    form = forms.CommentForm(request.POST or None)
    if form.is_valid():
        new = form.save(commit=False)
        new.author = request.user
        new.post = post
        new.save()
    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.select_related('author').filter(
        author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request, "follow.html",
                  {"page": page, "paginator": paginator})


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(User, username=username)
    follow = get_object_or_404(Follow, user=user, author=author)
    follow.delete()
    return redirect("profile", username=username)
