import json

from watson_developer_cloud import NaturalLanguageClassifierV1 as NLPService
from watson_developer_cloud import WatsonException

from .baseservice import BaseService


class NLPUtils(BaseService):
  def __init__(self, app):
    super(NLPUtils, self).__init__("natural_language_classifier")
    self.app = app
    self.service = NLPService(username=self.getUser(), 
                                              password=self.getPassword()) 

  def getNLPService(self):
    return self.service
 
