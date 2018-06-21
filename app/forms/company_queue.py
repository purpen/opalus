# coding: utf-8
from wtforms import TextAreaField, StringField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange
from flask_wtf import FlaskForm
from bson import ObjectId

#from .base import BaseForm
from ..models.company_queue import CompanyQueue
#from ..helpers import *

class SaveForm(FlaskForm):
    id = StringField()
    d3in_id = IntegerField()
    number = IntegerField()
    name = StringField()
    remark = StringField()
    kind = IntegerField()
    type = IntegerField()
    in_grap = IntegerField() # 是否完成站内抓取
    out_grap = IntegerField() # 是否完成站外抓取
    grap_times = IntegerField() # 追加次数
    tyc_status = IntegerField() # 天眼查 抓取进度: 0.未抓取；1.抓取中；2.失败；5.完成；
    bd_status = IntegerField() # 百度 抓取进度: 0.未抓取；1.抓取中；2.失败；5.完成；
    last_on = DateTimeField()    # 最后一次追加时间
    status = IntegerField()    # 状态: 0.禁用；1.启用

    def update(self):
        id = self.data['id']
        item = CompanyQueue.objects(_id=ObjectId(id)).first()
        if not item:
            raise ValueError('内容不存在!')
        data = self.data
        ok = item.update(**data)
        return ok

    def save(self, **param):
        data = self.data;
        data.pop('id')
        item = CompanyQueue(**data)
        item.save()
        return item


class setStatus(FlaskForm):
    id = StringField()
    status = IntegerField()

    def set_status(self):
        id = self.data['id']
        item = CompanyQueue.objects(_id=ObjectId(id)).first()
        if not item:
            raise ValueError('内容不存在!')
        data = {}
        data['status'] = self.data['status']
        ok = item.update(**data)
        return ok

