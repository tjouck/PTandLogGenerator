# -*- coding: utf-8 -*-
"""
Created on Sat May 20 14:40:03 2017

@author: lucp8356
"""

class CaseAttribute():
    def __init__(self,label,type='bool'):
        self.id = ''
        self.name = label
        self.type = type
    
    def assign_value(self,value):
        self.value = value