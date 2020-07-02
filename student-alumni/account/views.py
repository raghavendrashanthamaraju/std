from django.http import HttpResponse, JsonResponse,HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from common.decorators import ajax_required
from actions.utils import create_action
from actions.models import Action
from .forms import LoginForm, UserRegistrationForm, \
                   UserEditForm, ProfileEditForm
from .models import Profile, Contact
from django.shortcuts import render, get_object_or_404,redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from django.core.mail import send_mail
from django.db.models import Count
from taggit.models import Tag
from .models import Post, Comment
from .forms import EmailPostForm, CommentForm,PostForm


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request,
                                username=cd['username'],
                                password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated '\
                                        'successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'account/login.html', {'form': form})
@login_required
def myposts(request,tag_slug=None):
        object_list = Post.published.filter(user=request.user)
        tag = None

        if tag_slug:
            tag = get_object_or_404(Tag, slug=tag_slug)
            object_list = object_list.filter(tags__in=[tag])

        paginator = Paginator(object_list, 3) # 3 posts in each page
        page = request.GET.get('page')
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer deliver the first page
            posts = paginator.page(1)
        except EmptyPage:
            # If page is out of range deliver last page of results
            posts = paginator.page(paginator.num_pages)
        # Display all actions by default
        actions = Action.objects.filter(user=request.user)
        following_ids = request.user.following.values_list('id',
                                                           flat=True)
        if following_ids:
            # If user is following others, retrieve only their actions
            actions = actions.filter(user_id__in=following_ids)
        actions = actions.select_related('user', 'user__profile')\
                         .prefetch_related('target')[:10]

        return render(request,
                          'account/dashboard.html',
                          {'section': 'dashboard',
                          'actions': actions,
                           'page': page,
                            'posts': posts,
                            'tag': tag,})

@login_required
def dashboard(request,tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    # Display all actions by default
    actions = Action.objects.all()
    following_ids = request.user.following.values_list('id',
                                                       flat=True)
    if following_ids:
        # If user is following others, retrieve only their actions
        actions = actions.filter(user_id__in=following_ids)
        actions = actions.select_related('user', 'user__profile')\
                     .prefetch_related('target')[:8]

    paginator = Paginator(object_list, 3) # 3 posts in each page

    page = request.GET.get('page')
    try:
        posts = paginator.page(page)

    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)

    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)
    context={'section': 'dashboard',
     'actions': actions,'page': page,
      'posts': posts,
      'tag': tag,}
    return render(request,
                  'account/dashboard.html',
                 context )


def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            # Set the chosen password
            new_user.set_password(
                user_form.cleaned_data['password'])
            # Save the User object
            new_user.save()
            # Create the user profile
            Profile.objects.create(user=new_user)
            create_action(new_user, 'has created an account')
            return render(request,
                          'account/register_done.html',
                          {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request,
                  'account/register.html',
                  {'user_form': user_form})


@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user,
                                 data=request.POST)
        profile_form = ProfileEditForm(instance=request.user.profile,
                                       data=request.POST,
                                       files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Error updating your profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    return render(request,
                  'account/edit.html',
                  {'user_form': user_form,
                   'profile_form': profile_form})


@login_required
def user_list(request):
    users = User.objects.filter(is_active=True)
    return render(request,
                  'account/user/list.html',
                  {'section': 'people',
                   'users': users})


@login_required
def user_detail(request,username):
    user = get_object_or_404(User,
                             username=username,
                             is_active=True)
    dob=Profile.objects.get(user=user).date_of_birth

    return render(request,
                  'account/user/detail.html',
                  {'section': 'people',
                   'user': user,
                   'dob':dob})


@ajax_required
@require_POST
@login_required
def user_follow(request):
    user_id = request.POST.get('id')
    action = request.POST.get('action')
    if user_id and action:
        try:
            user = User.objects.get(id=user_id)
            if action == 'follow':
                Contact.objects.get_or_create(user_from=request.user,
                                              user_to=user)
                create_action(request.user, 'is following', user)
            else:
                Contact.objects.filter(user_from=request.user,
                                       user_to=user).delete()
            return JsonResponse({'status':'ok'})
        except User.DoesNotExist:
            return JsonResponse({'status':'ko'})
    return JsonResponse({'status':'ko'})
@login_required
def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])

    paginator = Paginator(object_list, 3) # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)

    return render(request,
                  'account/dashboard.html',
                  {'page': page,
                   'posts': posts,
                   'tag': tag,
                   'section': 'dashboard'})

@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST,request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            form.save_m2m()
            form = PostForm()
            create_action(request.user, 'has posted',post)
            return HttpResponseRedirect('/account/')

    else:
        form = PostForm()
    return render(request, 'blog/post/create-view.html', {'form': form})

@login_required
def post_model_update_view(request,id):
    obj=get_object_or_404(Post,id=id)
    form = PostForm(request.POST or None,instance=obj)
    if form.is_valid():
        obj=form.save(commit=False)
        obj.save()
        form.save_m2m()
    context={"title":obj.title,"form":form}
    template="blog/post/update-view.html"
    return render(request,template,context)


@login_required
def post_detail(request, year, month, day, post):
     post = get_object_or_404(Post, slug=post,
                                    status='published',
                                    publish__year=year,
                                    publish__month=month,
                                    publish__day=day)

     # List of active comments for this post
     comments = post.comments.filter(active=True)

     new_comment = None

     if request.method == 'POST':
         # A comment was posted
         comment_form = CommentForm(data=request.POST)
         if comment_form.is_valid():
             # Create Comment object but don't save to database yet

             new_comment = comment_form.save(commit=False)

             # Assign the current post to the comment
             new_comment.post = post
             new_comment.name=request.user
             # Save the comment to the database
             new_comment.save()
             comment_form = CommentForm(data=request.POST)
             create_action(request.user, 'has commented on', post)
     else:
         comment_form = CommentForm()

     # List of similar posts
     post_tags_ids = post.tags.values_list('id', flat=True)
     similar_posts = Post.published.filter(tags__in=post_tags_ids)\
                                   .exclude(id=post.id)
     similar_posts = similar_posts.annotate(same_tags=Count('tags'))\
                                 .order_by('-same_tags','-publish')[:4]

     return render(request,
                   'blog/post/detail.html',
                   {'post': post,
                    'comments': comments,
                    'new_comment': new_comment,
                    'comment_form': comment_form,
                    'similar_posts': similar_posts})


class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'


def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(
                                          post.get_absolute_url())
            subject = '{} ({}) recommends you reading "{}"'.format(cd['name'], cd['email'], post.title)
            message = 'Read "{}" at {}\n\n{}\'s comments: {}'.format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'project.alumni.django@gmail.com',['jaladikarthik30@gmail.com'])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form,
                                                    'sent': sent})
