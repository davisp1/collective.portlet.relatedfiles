from plone.testing import z2

from plone.app.testing import *
import collective.portlet.relatedfiles

FIXTURE = PloneWithPackageLayer(zcml_filename="configure.zcml",
                                zcml_package=collective.portlet.relatedfiles,
                                additional_z2_products=[],
                                gs_profile_id='collective.portlet.relatedfiles:default',
                                name="collective.portlet.relatedfiles:FIXTURE")

INTEGRATION = IntegrationTesting(bases=(FIXTURE,),
                        name="collective.portlet.relatedfiles:Integration")

FUNCTIONAL = FunctionalTesting(bases=(FIXTURE,),
                        name="collective.portlet.relatedfiles:Functional")

