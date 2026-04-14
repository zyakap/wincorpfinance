
# Media Storage to be served locally
from django.conf import settings
from django.conf.urls.static import static
# others
from django.contrib import admin
from django.urls import include, path, re_path

from custom.views import home, about, contact, clients, dcc, demo, how_to_videos

urlpatterns = [

    path('appadmin/', admin.site.urls),
    path('__debug__/', include('debug_toolbar.urls')), 
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin/', include('admin1.urls')),
    path('staff/', include('staff.urls')),
    path('loan/', include('loan.urls')),
    path('message/', include('message.urls')),
    path('support/', include('support.urls')),
    path('custom/', include('custom.urls')),
    path('API/', include('api.urls')),
    path('report/', include('report.urls')),
    path('dcc/', include('dcc.urls')),

    #website url paths
    re_path(r'^$', home, name='home'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('clients/', clients, name='clients'),
    path('dcc/', dcc, name='dcc'),
    path('demo/', demo, name='demo'),
    path('how-to-videos/', how_to_videos, name='how_to_videos'),

    
    
    
    #Django Jet Admin
    #path('jet/', include('jet.urls', 'jet')),
    #path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
]

# Media Storage to be served locally
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    



