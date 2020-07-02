from django.urls import path,re_path
from . import views


app_name = 'blog'
urlpatterns = [
    # post views
    path('', views.post_list, name='post_list'),
    # path('', views.PostListView.as_view(), name='post_list'),
    path('<int:year>/<int:month>/<int:day>/<slug:post>/',
          views.post_detail,
          name='post_detail'),
    path('<int:post_id>/share/',
         views.post_share, name='post_share'),
    path('tag/<slug:tag_slug>/',
         views.post_list, name='post_list_by_tag'),
         path('create/',views.post_new, name='create'),
         path('myposts/',views.myposts, name='myposts'),
         re_path(r'^(?P<id>\d+)/edit$',views.post_model_update_view, name='update')
]
