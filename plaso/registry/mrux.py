#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2012 The Plaso Project Authors.
# Please see the AUTHORS file for details on individual authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This file contains a simple MRUx plugin for Plaso."""
import construct

from plaso.lib import event
from plaso.lib import win_registry_interface


class MRUexPlugin(win_registry_interface.ValuePlugin):
  """A simple generic MRU plugin for entries with a MRUListEx."""

  REG_TYPE = 'any'
  REG_VALUES = frozenset(['MRUListEx', '0'])
  URLS = [u'http://forensicartifacts.com/2011/02/recentdocs/']

  LIST_STRUCT = construct.Range(1, 500, construct.ULInt32('entry_number'))

  def GetText(self, mru_entry):
    """Return a string from a MRU value."""
    val = self._key.GetValue(mru_entry)
    if val:
      string = u''
      if val.GetTypeStr() == 'SZ' or val.GetTypeStr() == 'EXPAND_SZ':
        string = val.GetData()
      elif val.GetTypeStr() == 'BINARY':
        string = val.GetRawData().decode('utf_16_le', 'ignore').split('\x00')[0]
      return string
    return u''

  def GetEntries(self):
    """Extract EventObjects from a MRU list."""
    mru_list_data = self._key.GetValue('MRUListEx')
    raw_data = mru_list_data.GetRawData()

    try:
      mru_list = self.LIST_STRUCT.parse(raw_data)
    except construct.FieldError:
      logging.warning(u'Unable to parse the MRU key: %s', self._key.path)
      return

    event_timestamp = self._key.timestamp

    for nr, entry in enumerate(mru_list):
      # MRU lists are terminated with 0xFFFFFFFF.
      if entry == 0xFFFFFFFF:
        break
      text_dict = {}
      value_text = u'MRUListEx Entry %s (nr. %d)' % (unicode(entry), nr + 1)
      text_dict[value_text] = self.GetText(unicode(entry))
      evt = event.WinRegistryEvent(self._key.path, text_dict, event_timestamp)
      evt.source_append = ': MRUx List'
      event_timestamp = 0
      yield evt

  def Process(self, key):
    """Determine if we can process this registry key or not."""
    if 'BagMRU' in key.path or 'Explorer\\StreamMRU' in key.path:
      return None

    return super(MRUexPlugin, self).Process(key)
