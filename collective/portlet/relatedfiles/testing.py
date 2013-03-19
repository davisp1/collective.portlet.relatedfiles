from plone.testing import z2

from plone.app.testing import *
import collective.relatedfiles

FIXTURE = PloneWithPackageLayer(zcml_filename="configure.zcml",
                                zcml_package=collective.relatedfiles,
                                additional_z2_products=[],
                                gs_profile_id='collective.relatedfiles:default',
                                name="collective.relatedfiles:FIXTURE")

INTEGRATION = IntegrationTesting(bases=(FIXTURE,),
                        name="collective.relatedfiles:Integration")

FUNCTIONAL = FunctionalTesting(bases=(FIXTURE,),
                        name="collective.relatedfiles:Functional")

