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

_NB_DESC_CHAR = 100

# used to sanitize search
def quotestring(s):
    return '"%s"' % s


def quote_bad_chars(s):
    bad_chars = ["(", ")"]
    for char in bad_chars:
        s = s.replace(char, quotestring(char))
    return s

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

    including_video = schema.Bool(
        title=_(u"Search in videos"),
        description=_(u"If selected, we will search on Files and specialy Video."),
        default=False,
    )
    
    including_audio = schema.Bool(
        title=_(u"Search in audios"),
        description=_(u"If selected, we will search on Files and specialy Audio."),
        default=False,
    )
    
    including_pdf = schema.Bool(
        title=_(u"Search in pdf"),
        description=_(u"If selected, we will search on Files and specialy Pdf."),
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
                 including_video=False,
                 including_pdf=False,
                 including_audio=False,
                 only_subject=False,
                 display_description=True,
                 display_all_fallback=True,
                ):
        self.portlet_title = portlet_title
        self.count = count
        self.including_video = including_video
        self.including_audio = including_audio
        self.including_pdf = including_pdf
        self.only_subject = only_subject
        self.display_description = display_description
        self.display_all_fallback = display_all_fallback

    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen.
        """
        return self.portlet_title or _(u"Related Files")

class Renderer(base.Renderer):
    """Portlet renderer.

    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """
    
    _template = ViewPageTemplateFile('relatedfiles.pt')

    @ram.cache(render_cachekey)
    def render(self):
        return xhtml_compress(self._template())
    
    @property
    def available(self):
        return len(self._data())>0

    def getRelatedFiles(self):
        return self._data()

    def currenttime(self):
        return time.time()

    def trimDescription(self, desc):
        if len(desc) > _NB_DESC_CHAR:
                res = desc[0:_NB_DESC_CHAR]
                return res[:res.rfind(" ")] + " ..."
        else:
                return desc
    def uniq(self, alist):    # Fastest order preserving
        set = {}
        return [set.setdefault(e, e) for e in alist if e not in set]
    
    def getPortletTitle(self):
        return self.data.portlet_title

    def displayDescription(self):
        return self.data.display_description
    
    def _contents(self):
        contents = []
        # Collection
        if IATTopic.providedBy(self.context):
            try:
                contents = self.context.queryCatalog(
                contentFilter={'sort_limit': 6})
            except:
                pass
        # probably a folder
        else:
            contents = self.context.getFolderContents()

        # Make sure the content is not too big
        contents = contents[:6]

        return contents

    def _itemQuery(self, value):
        search_query = []
        keywords = list(value.Subject())
        # Include words from title in the search query
        title = value.Title().split()
        search_query = title + keywords

        # Filter out boolean searches and keywords with only one letter
        search_query = [res
                        for res in search_query
            if not res.lower() in ['not', 'and', 'or'] and len(res) != 1]

        return search_query

    def _itemsQuery(self, values):
        query = ''
        items = []
        for item in values:
            items += self._itemQuery(item)
        # remove duplicated search keywords
        items = self.uniq(items)
        query = " OR ".join(items)

        return query

    @memoize
    def _data(self):
        plone_tools = getMultiAdapter((self.context, self.request),
                                      name=u'plone_tools')
        context = aq_inner(self.context)
        here_path = ('/').join(context.getPhysicalPath())

        # Exclude items from related if contained in folderish
        content = []
        if self.context.isPrincipiaFolderish:
            content = self._contents()

        exclude_items = map(lambda x: x.getPath(), content)
        exclude_items += [here_path]

        search_query = self._query()
        search_query = quote_bad_chars(search_query)
        #print 'search_query = '+search_query

        catalog = plone_tools.catalog()
        limit = self.data.count
        # increase by one since we'll get the current item
        extra_limit = limit + len(exclude_items)

        query = dict(portal_type=('File',),
                     SearchableText=search_query,
                     sort_limit=extra_limit)
        
        if self.data.only_subject:
            query['Subject'] = self.context.Subject()
            if 'SearchableText' in query:
                del query['SearchableText']
        
        results = catalog(**query)

        types=[]
        if self.data.including_video:types+="video"
        if self.data.including_pdf:types+="pdf"
        if self.data.including_audio:types+="audio"
        
        self.all_results=[res for res in results if ( ( res.getIcon in types ) and ( res.getPath() not in exclude_items ) )]

        # No related items were found
        # Get the latest modified articles

        #if self.data.show_recent_items and self.all_results == []:
        if self.data.display_all_fallback and (self.all_results == []):
            results = catalog(portal_type=self.data.allowed_types,
                              sort_on='modified',
                              sort_order='reverse',
                              sort_limit=extra_limit)
            self.all_results = [res for res in results if ( ( res.getIcon in types ) and ( res.getPath() not in exclude_items ) )]

        return self.all_results[:limit]

    @property
    def showRelatedItemsLink(self):
        """Determine if the 'more...' link needs to be displayed
        """
        # if we have more results than are shown, show the more link
        if len(self.all_results) > self.data.count:
            return True
        return False

class AddForm(base.AddForm):
    """Portlet add form.

    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """
    form_fields = form.Fields(IRelatedFiles)
    label = _(u"Add Related Files Portlet")
    description = _(u"This portlet displays recent Related Files.")

    def create(self, data):
        return Assignment(
            portlet_title=data.get('portlet_title', u'Related Files'),
            count=data.get('count', 5),
            including_video=data.get('including_video', False),
            including_audio=data.get('including_audio', False),
            including_pdf=data.get('including_pdf', False),
            only_subject=data.get('only_subject', False),
            display_all_fallback=data.get('display_all_fallback', True),
            display_description=data.get('display_description', True),
        )


class EditForm(base.EditForm):
    """Portlet edit form.

    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """
    form_fields = form.Fields(IRelatedFiles)
    label = _(u"Edit Related Files Portlet")
    description = _(u"This portlet displays related items based on "
                     "keywords matches, title.")