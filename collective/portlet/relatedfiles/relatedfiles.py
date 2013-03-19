from ZTUtils import make_query

import time
from zope.interface import implements
from Products.ATContentTypes.interface import IATTopic

from zope import schema
from zope.formlib import form
from zope.component import getMultiAdapter

from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from plone.app.portlets.cache import render_cachekey
from plone.memoize import ram
from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize

from Acquisition import aq_inner

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.portlet.relatedfiles import RelatedItemsMessageFactory as _

try:
    from collective.contentleadimage.config import IMAGE_FIELD_NAME
    from collective.contentleadimage.leadimageprefs import ILeadImagePrefsForm
    from zope.component import getUtility
    from Products.CMFPlone.interfaces import IPloneSiteRoot
    LEADIMAGE_EXISTS = True
except ImportError:
    LEADIMAGE_EXISTS = False


class IRelatedFiles(IPortletDataProvider):
    """A portlet

    It inherits from IPortletDataProvider because for this portlet, the
    data that is being rendered and the portlet assignment itself are the
    same.
    """

    portlet_title = schema.TextLine(
        title=_(u'Portlet title'),
        description=_(u'Title in portlet.'),
        required=True,
        default=_(u'Related Files')
    )

    count = schema.Int(
        title=_(u'Number of related files to display'),
        description=_(u'How many related files to list.'),
        required=True,
        default=10
    )

    only_video = schema.Bool(
        title=_(u"Search only in videos"),
        description=_(u"If selected, we will search only File and specialy Video."),
        default=False,
    )
    
    only_audio = schema.Bool(
        title=_(u"Search only in audios"),
        description=_(u"If selected, we will search only File and specialy Audio."),
        default=False,
    )
    
    only_pdf = schema.Bool(
        title=_(u"Search only in pdf"),
        description=_(u"If selected, we will search only File and specialy Pdf."),
        default=False,
    )
    
    only_subject = schema.Bool(
        title=_(u"Search only on subject"),
        description=_(u"If selected, we will search only on content subject."),
        default=False,
    )

    display_all_fallback = schema.Bool(
        title=_(u"Display recent files on no results fallback"),
        description=_(u"If selected, we will display all "
                      "allowed files where there are no results for "
                      "our current related files query"),
        default=True,
    )

    display_description = schema.Bool(
        title=_(u"Display description"),
        description=_(
            u"If selected, we will show the content short description"),
        default=True,
    )

class Assignment(base.Assignment):
    """Portlet assignment.

    This is what is actually managed through the portlets UI and associated
    with columns.
    """

    implements(IRelatedFiles)

    def __init__(self,
                 portlet_title=u'Related Files',
                 count=5,
                 only_video=False,
                 only_pdf=False,
                 only_audio=False,
                 only_subject=False,
                 display_description=True,
                 display_all_fallback=True,
                ):
        self.portlet_title = portlet_title
        self.count = count
        self.only_video = only_video
        self.only_audio = only_audio
        self.only_pdf = only_pdf
        self.only_subject = only_subject
        self.display_description = display_description
        self.display_all_foallback = display_all_fallback

    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen.
        """
        return self.portlet_title or _(u"Related Files")