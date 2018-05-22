from flask import request, jsonify, current_app
from . import api
import datetime
from app.models.design_company import DesignCompany
from app.helpers.pager import Pager
from app.helpers.block import get_block_content
from app.forms.design_company import SaveForm
from app.helpers.common import force_int

## 列表
@api.route('/design_company/list')
def design_company_list():

    query = {}
    meta = {}
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = int(request.args.get('status', 0))
    craw_user_id = int(request.args.get('craw_user_id', 0))
    deleted = int(request.args.get('deleted', 0))
    kind = int(request.args.get('kind', 0))
    name = request.args.get('name', '')

    if kind:
        query['kind'] = kind

    if status == -1:
        query['status'] = 0
    if status == 1:
        query['status'] = 1
    else:
        pass

    if name:
        query['name'] = name

    if craw_user_id:
        if craw_user_id == -1:
            query['craw_user_id'] = 0
        else:
            query['craw_user_id'] = craw_user_id

    query['deleted'] = deleted

    try:
        data = DesignCompany.objects(**query).order_by('-created_at').paginate(page=page, per_page=per_page)
        total_count = DesignCompany.objects(**query).count()

        # 过滤数据
        for i, d in enumerate(data.items):
            data.items[i]._id = str(d._id)
            craw_user = '--'
            if d.craw_user_id:
                if d.craw_user_id == 1:
                    craw_user = '军平'
                if d.craw_user_id == 2:
                    craw_user = '小董'
                
            data.items[i].craw_user = craw_user

        meta['rows'] = data.items
    except(Exception) as e:
        meta['rows'] = []
        total_count = 0

    meta['total_count'] = total_count
    meta['page'] = page
    meta['per_page'] = per_page

    return jsonify(code=0, message='success!', data=meta)

## 查看
@api.route('/design_company/view')
def design_company_view():
    number = request.args.get('number', None)
    if not number:
        return jsonify(code=3001, message='编号不存在!')

    design_company = DesignCompany.objects(number=number).first()
    if not design_company:
        return jsonify(code=3002, message='公司不存在!')

    design_company._id = str(design_company._id)
    design_company.tags_label = ','.join(design_company.tags)
    
    return jsonify(code=0, message='success!', data=design_company)

## 保存/更新公司信息
@api.route('/design_company/update', methods=['POST'])
def design_company_update():
    # 检测接口是否打开
    conf = get_block_content('design_grap_switch')
    if not conf:
        return jsonify(code=3002, message='接口已关闭!')

    conf_arr = conf.strip().strip('|').split('|')

    current_app.logger.debug(conf_arr)
    if len(conf_arr) == 0:
        return jsonify(code=3002, message='接口已关闭!!')
    if int(conf_arr[0]) != 1:
        return jsonify(code=3002, message='接口已关闭!!!')

    form = SaveForm(request.values)
    if not form.validate_on_submit():
        return jsonify(code=3004, message=str(form.errors))

    number = request.values.get('number', None)
    data = request.values.to_dict()

    for key in request.values:
        data[key] = data[key].strip()
        if not request.values.get(key):
            data.pop(key)

    # 公司数量整理
    if 'company_count' in data:
        if ',' in data['company_count']:
            company_count_arr = data['company_count'].split(',')
            company_count = 0
            for n in company_count_arr:
               company_count += force_int(n)
            data['company_count'] = str(company_count)

    if not number:
        return jsonify(code=3001, message='编号不存在!')

    try:
        design_company = DesignCompany.objects(number=number).first()
        if not design_company:
            return jsonify(code=3002, message='内容不存在!')

        if 'number' in data:
            data.pop('number')
        if 'perfect_degree' in data:
            data.pop('perfect_degree')

        if not data:
            return jsonify(code=3003, message='至少传入一个参数!')

        data['inc__craw_count'] = 1 # 自增
        data['last_on'] = datetime.datetime.now()
        design_company.update(**data)

        if design_company:
            return jsonify(code=0, message='success!', data=data)
        else:
            return jsonify(code=3010, message='更新失败！')

    except(Exception) as e:
        return jsonify(success=False, message=str(e))


