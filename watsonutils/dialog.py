import json

from watson_developer_cloud import DialogV1 as DialogService
from watson_developer_cloud import WatsonException

from .baseservice import BaseService


class DialogUtils(BaseService):
  def __init__(self, app):
    super(DialogUtils, self).__init__("dialog_service")
    self.app = app
    self.service = DialogService(username=self.getUser(), 
                                              password=self.getPassword()) 

  def getDialogService(self):
    return self.service
 
  def getDialogs(self):
    dialogs = self.getDialogService()
    dialogs = dialogs.get_dialogs()
    return dialogs

  def createDialog(self, dialog_file, dialogname):
    dialog = self.getDialogService()
    dialog = dialog.create_dialog(dialog_file=dialog_file, name=dialogname)
    return dialog

  def getConversation(self,dialog_id):
    dialog = self.getDialogService()
    response = dialog.conversation(dialog_id)
    return response
    
