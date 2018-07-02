# coding: utf-8
from app.extensions import celery
from app.helpers.common import force_int
from app.models.design_conf import DesignConf
from app.models.design_company import DesignCompany
from app.models.design_record import DesignRecord
from flask import current_app, jsonify
import requests
import json
from app.env import cf

# 公司排行统计
@celery.task()
def company_stat(mark, no):

    conf = DesignConf.objects(mark=mark).first()
    if not conf:
        print("配置文件不存在！")
        return

    page = 1
    perPage = 100
    isEnd = False
    successStatCount = 0
    failStatCount = 0
    query = {}
    query['deleted'] = 0
    query['status'] = 1

    while not isEnd:
        data = DesignCompany.objects(**query).order_by('-created_at').paginate(page=page, per_page=perPage)
        if not data:
            print("get data is empty! \n")
            continue

        # 过滤数据
        for i, d in enumerate(data.items):
            options = {
                'company': d,
                'conf': conf,
                'mark': mark,
                'no': no
            }
            result = company_stat_core(**options)
            if result['success']:
                successStatCount += 1
            else:
                continue

        print("current page %s: \n" % page)
        page += 1
        if len(data.items) < perPage:
            isEnd = True

    print("is over execute SuccessCount %d ---- failCount: %d\n" % (successStatCount, failStatCount))

    ## 统计平均分
    print("Begin stat average.....\n")
    company_average_stat(mark, no)

    # 更新排名
    print("Begin update ranking....\n")
    company_update_rank(mark, no)


# 公司平均分统计
@celery.task()
def company_average_stat(mark, no):

    page = 1
    perPage = 100
    isEnd = False
    total = 0
    successStatCount = 0
    failStatCount = 0
    query = {'mark': mark, 'no': no, 'status': 1, 'deleted': 0}
    nSortVal = '-ave_score'
    f = 1
    bs = 50
    bf = 0.5

    maxBase = DesignRecord.objects(**query).order_by('-base_score', nSortVal).first()   # 基础运作力
    maxBusiness = DesignRecord.objects(**query).order_by('-business_score', nSortVal).first()   # 商业决策力
    maxInnovate = DesignRecord.objects(**query).order_by('-innovate_score', nSortVal).first()   # 创新交付力
    maxDesign = DesignRecord.objects(**query).order_by('-design_score', nSortVal).first()   # 品牌溢价力
    maxEffect = DesignRecord.objects(**query).order_by('-effect_score', nSortVal).first()   # 客观公信力
    maxCredit = DesignRecord.objects(**query).order_by('-credit_score', nSortVal).first()   # 风险应激力

    options = {
        'max_base': maxBase,
        'max_business': maxBusiness,
        'max_innovate': maxInnovate,
        'max_design': maxDesign,
        'max_effect': maxEffect,
        'max_credit': maxCredit,
        'f': 1,
        'bs': 50,
        'bf': 0.5
    }

    while not isEnd:
        data = DesignRecord.objects(**query).paginate(page=page, per_page=perPage)
        if not data:
            print("get data is empty! \n")
            continue

        # 过滤数据
        for i, d in enumerate(data.items):
            result = average_stat_core(d, **options)
            if not result['success']:
                print(result['message'])
                continue

            print("更新成功---number: %s.\n" % d.number)
            # 更新到铟果
            dMark = cf.get('rank', 'mark')
            dNo = cf.getint('rank', 'no') 
            if mark == dMark and no == dNo:
                if result['data'].d3in_id:
                    print("开始更新到铟果[%d]...." % result['data'].d3in_id)
                    ave_update_d3in(result['data'].d3in_id, result['data'])
            total += 1

        print("current page %s: \n" % page)
        page += 1
        if len(data.items) < perPage:
            isEnd = True

    print("is over execute count %s\n" % total)


# 公司排名统计rank
@celery.task()
def company_update_rank(mark, no):

    page = 1
    perPage = 100
    isEnd = False
    total = 0
    successStatCount = 0
    failStatCount = 0
    query = {'mark': mark, 'no': no, 'status': 1, 'deleted': 0}

    while not isEnd:
        data = DesignRecord.objects(**query).order_by('-ave_score', '-base_average').paginate(page=page, per_page=perPage)
        if not data:
            print("get data is empty! \n")
            continue

        # 过滤数据
        for i, d in enumerate(data.items):
            scoreQuery = {}
            scoreQuery['rank'] = int((page -1) * perPage + i + 1)
            ok = d.update(**scoreQuery)
            if not ok:
              print("更新失败~!")
              continue

            print("更新成功---number: %s.\n" % d.number)
            total += 1

        print("current page %s: \n" % page)
        page += 1
        if len(data.items) < perPage:
            isEnd = True

    print("is over execute count %s\n" % total)


# 公司排行统计--Core
@celery.task()
def company_stat_core(**options):
    result = {'success': False, 'message': ''}
    d = options['company']
    conf = options['conf']
    mark = options['mark']
    no = options['no']
    ## 是否入驻铟果
    is_d3in = 0
    ## 基本信息统计
    baseConf = {
        'in_d3ing': 0,
        'key_personnel_count': 0,
        'chage_record_count': 0,
        'affiliated_agency_count': 0,
        'financing_count': 0,
        'core_team_count': 0,
        'enterprise_business_count': 0,
        'competitor_count': 0,
        'bid_count': 0,
    }
    # 入驻铟果
    if d.d3ing_id:
        is_d3in = 1
        baseConf['in_d3ing'] = conf['in_d3ing']
    # 主要成员
    if d.key_personnel_count:
        baseConf['key_personnel_count'] = d.key_personnel_count * conf['key_personnel_count']
    # 股东信息
    if d.shareholder_count:
        baseConf['shareholder_count'] = d.shareholder_count * conf['shareholder_count']
    # 变更信息
    if d.chage_record_count:
        baseConf['chage_record_count'] = d.chage_record_count * conf['chage_record_count']
    # 分支机构
    if d.affiliated_agency_count:
        baseConf['affiliated_agency_count'] = d.affiliated_agency_count * conf['affiliated_agency_count']
    # 融资
    if d.financing_count:
        baseConf['financing_count'] = d.financing_count * conf['financing_count']
    # 核心团队
    if d.core_team_count:
        baseConf['core_team_count'] = d.core_team_count * conf['core_team_count']
    # 企业业务
    if d.enterprise_business_count:
        baseConf['enterprise_business_count'] = d.enterprise_business_count * conf['enterprise_business_count']
    # 竞品信息
    if d.competitor_count:
        baseConf['competitor_count'] = d.competitor_count * conf['competitor_count']
    # 招投标
    if d.bid_count:
        baseConf['bid_count'] = d.bid_count * conf['bid_count']

    ## 统计基本信息分值
    baseScore = 0
    for k, v in baseConf.items():
        baseScore += v


    ## 商业力指数
    businessConf = {
        'scale': 0,
        'registered_capital_format': 0,
        'investment_abroad_count': 0,
        'annual_return_count': 0,
        'branch': 0,
        'company_count': 0,
    }

    # 公司规则
    if d.scale:
        if d.scale == 1:
            businessConf['scale'] = conf['scale_a']
        elif d.scale == 2:
            businessConf['scale'] = conf['scale_b']
        elif d.scale == 3:
            businessConf['scale'] = conf['scale_c']
        elif d.scale == 4:
            businessConf['scale'] = conf['scale_d']
        elif d.scale == 5:
            businessConf['scale'] = conf['scale_e']

    # 注册资金
    if d.registered_capital_format:
        if d.registered_capital_format == 1:
            businessConf['registered_capital_format'] = conf['registered_capital_format_a']
        elif d.registered_capital_format == 2:
            businessConf['registered_capital_format'] = conf['registered_capital_format_b']
        elif d.registered_capital_format == 3:
            businessConf['registered_capital_format'] = conf['registered_capital_format_c']
        elif d.registered_capital_format == 4:
            businessConf['registered_capital_format'] = conf['registered_capital_format_d']
        elif d.registered_capital_format == 5:
            businessConf['registered_capital_format'] = conf['registered_capital_format_e']

    # 对外投资
    if d.investment_abroad_count:
        businessConf['investment_abroad_count'] = d.investment_abroad_count * conf['investment_abroad_count']
    # 公司年报
    if d.annual_return_count:
        businessConf['annual_return_count'] = d.annual_return_count * conf['annual_return_count']
    # 分公司数
    if d.branch:
        businessConf['branch'] = force_int(d.branch) * conf['branch']
    # 法人公司数
    if d.company_count:
        businessConf['company_count'] = force_int(d.company_count) * conf['company_count']


    ## 统计商业力指数分值
    businessScore = 0
    for k, v in businessConf.items():
        businessScore += v


    ## 创新力指数
    innovateConf = {
        'trademark_count': 0,
        'patent_count': 0,
        'software_copyright_count': 0,
        'works_copyright_count': 0,
        'icp_count': 0,
    }

    # 商标
    if d.trademark_count:
        if d.trademark_count < 5:
            innovateConf['trademark_count'] = conf['trademark_count_a']
        elif d.trademark_count >= 5 and d.trademark_count < 10:
            innovateConf['trademark_count'] = conf['trademark_count_b']
        elif d.trademark_count >= 10 and d.trademark_count < 50:
            innovateConf['trademark_count'] = conf['trademark_count_c']
        elif d.trademark_count >= 50 and d.trademark_count < 100:
            innovateConf['trademark_count'] = conf['trademark_count_d']
        elif d.trademark_count >= 100 and d.trademark_count < 500:
            innovateConf['trademark_count'] = conf['trademark_count_e']
        elif d.trademark_count >= 500:
            innovateConf['trademark_count'] = conf['trademark_count_f']

    # 专利
    if d.patent_count:
        if d.patent_count < 5:
            innovateConf['patent_count'] = conf['patent_count_a']
        elif d.patent_count >= 5 and d.patent_count < 10:
            innovateConf['patent_count'] = conf['patent_count_b']
        elif d.patent_count >= 10 and d.patent_count < 50:
            innovateConf['patent_count'] = conf['patent_count_c']
        elif d.patent_count >= 50 and d.patent_count < 100:
            innovateConf['patent_count'] = conf['patent_count_d']
        elif d.patent_count >= 100 and d.patent_count < 500:
            innovateConf['patent_count'] = conf['patent_count_e']
        elif d.patent_count >= 500:
            innovateConf['patent_count'] = conf['patent_count_f']
    # 软件著作权
    if d.software_copyright_count:
        if d.software_copyright_count < 5:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_a']
        elif d.software_copyright_count >= 5 and d.software_copyright_count < 10:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_b']
        elif d.software_copyright_count >= 10 and d.software_copyright_count < 50:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_c']
        elif d.software_copyright_count >= 50 and d.software_copyright_count < 100:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_d']
        elif d.software_copyright_count >= 100 and d.software_copyright_count < 500:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_e']
        elif d.software_copyright_count >= 500:
            innovateConf['software_copyright_count'] = conf['software_copyright_count_f']

    # 作品著作权
    if d.works_copyright_count:
        if d.works_copyright_count < 5:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_a']
        elif d.works_copyright_count >= 5 and d.works_copyright_count < 10:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_b']
        elif d.works_copyright_count >= 10 and d.works_copyright_count < 50:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_c']
        elif d.works_copyright_count >= 50 and d.works_copyright_count < 100:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_d']
        elif d.works_copyright_count >= 100 and d.works_copyright_count < 500:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_e']
        elif d.works_copyright_count >= 500:
            innovateConf['works_copyright_count'] = conf['works_copyright_count_f']
    # 网站备案
    if d.icp_count:
        innovateConf['icp_count'] = d.icp_count * conf['icp_count']

    ## 统计创新力指数分值
    innovateScore = 0
    for k, v in innovateConf.items():
        innovateScore += v


    ## 设计力指数
    designConf = {
        'design_center': 0,
        'design_case_count': 0,
        'd3in_case_count': 0,
        'red_star_award_count': 0,
        'innovative_design_award_count': 0,
        'china_design_award_count': 0,
        'dia_award_count': 0,
        'if_award_count': 0,
        'red_dot_award_count': 0,
        'idea_award_count': 0,
        'gmark_award_count': 0,
    }

    # 设计中心--省级/国家级
    if d.is_design_center:
        if d.is_design_center == 1:
            designConf['design_center'] = conf['design_center_province']
        elif d.is_design_center == 2:
            designConf['design_center'] = conf['design_center_county']

    # 抓取作品数
    if d.design_case_count:
        designConf['design_case_count'] = d.design_case_count * conf['design_case_count']
    # 铟果作品数
    if d.d3in_case_count:
        #designConf['d3in_case_count'] = d.d3in_case_count * conf['d3in_case_count']
        if d.d3in_case_count <= 5:
            designConf['d3in_case_count'] = conf['d3in_case_count_a']
        elif d.d3in_case_count > 5 and d.d3in_case_count <= 20:
            designConf['d3in_case_count'] = conf['d3in_case_count_b']
        elif d.d3in_case_count > 20 and d.d3in_case_count <= 50:
            designConf['d3in_case_count'] = conf['d3in_case_count_c']
        elif d.d3in_case_count > 50 and d.d3in_case_count <= 100:
            designConf['d3in_case_count'] = conf['d3in_case_count_d']
        elif d.d3in_case_count > 100 and d.d3in_case_count <= 500:
            designConf['d3in_case_count'] = conf['d3in_case_count_e']
        elif d.d3in_case_count > 500:
            designConf['d3in_case_count'] = conf['d3in_case_count_f']
            

    # 红星奖
    if d.red_star_award_count:
        designConf['red_star_award_count'] = d.red_star_award_count * conf['red_star_award_count']
    # 红棉奖
    if d.innovative_design_award_count:
        designConf['innovative_design_award_count'] = d.innovative_design_award_count * conf['innovative_design_award_count']
    # 中国好设计奖
    if d.china_design_award_count:
        designConf['china_design_award_count'] = d.china_design_award_count * conf['china_design_award_count']
    # 中国设计智造大奖
    if d.dia_award_count:
        designConf['dia_award_count'] = d.dia_award_count * conf['dia_award_count']
    # if奖
    if d.if_award_count:
        designConf['if_award_count'] = d.if_award_count * conf['if_award_count']
    # 红点奖
    if d.red_dot_award_count:
        designConf['red_dot_award_count'] = d.red_dot_award_count * conf['red_dot_award_count']
    # IDEA工业设计奖
    if d.idea_award_count:
        designConf['idea_award_count'] = d.idea_award_count * conf['idea_award_count']
    # G-Mark设计奖
    if d.gmark_award_count:
        designConf['gmark_award_count'] = d.gmark_award_count * conf['gmark_award_count']

    ## 统计设计力指数分值
    designScore = 0
    for k, v in designConf.items():
        designScore += v


    ## 影响力指数
    effectConf = {
        'is_high_tech': 0,
        'ty_score': 0,
        'ty_view_count': 0,
        'bd_hot_count': 0,
        'certification_count': 0,
        'cida_credit_rating': 0,
        'wx_public_count': 0,
    }

    # 高新企业
    if d.is_high_tech:
        effectConf['is_high_tech'] = conf['is_high_tech']
    # 天眼查分数
    if d.ty_score:
        effectConf['ty_score'] = d.ty_score * conf['ty_score']
    # 天眼查浏览数
    if d.ty_view_count:
        if d.ty_view_count < 100:
            effectConf['ty_view_count'] = conf['ty_view_count_a']
        elif d.ty_view_count >= 100 and d.ty_view_count < 500:
            effectConf['ty_view_count'] = conf['ty_view_count_b']
        elif d.ty_view_count >= 500 and d.ty_view_count < 2000:
            effectConf['ty_view_count'] = conf['ty_view_count_c']
        elif d.ty_view_count >= 2000 and d.ty_view_count < 5000:
            effectConf['ty_view_count'] = conf['ty_view_count_d']
        elif d.ty_view_count >= 5000 and d.ty_view_count < 10000:
            effectConf['ty_view_count'] = conf['ty_view_count_e']
        elif d.ty_view_count >= 10000:
            effectConf['ty_view_count'] = conf['ty_view_count_f']

    # 百度关键词热度(品牌名或简称)
    if d.baidu_brand_hot:
        if d.baidu_brand_hot < 10000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_a']
        elif d.baidu_brand_hot >= 10000 and d.baidu_brand_hot < 100000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_b']
        elif d.baidu_brand_hot >= 100000 and d.baidu_brand_hot < 500000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_c']
        elif d.baidu_brand_hot >= 500000 and d.baidu_brand_hot < 1000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_d']
        elif d.baidu_brand_hot >= 1000000 and d.baidu_brand_hot < 5000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_e']
        elif d.baidu_brand_hot >= 5000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_f']
    # 公司全称
    elif d.baidu_hot:
        if d.baidu_hot < 10000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_a']
        elif d.baidu_hot >= 10000 and d.baidu_hot < 200000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_b']
        elif d.baidu_hot >= 200000 and d.baidu_hot < 1000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_c']
        elif d.baidu_hot >= 1000000 and d.baidu_hot < 5000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_d']
        elif d.baidu_hot >= 5000000 and d.baidu_hot < 10000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_e']
        elif d.baidu_hot >= 10000000:
            effectConf['bd_hot_count'] = conf['bd_hot_count_f']

    # 资质证书
    if d.certification_count:
        effectConf['certification_count'] = d.certification_count * conf['certification_count']

    # 工会认证
    if d.cida_credit_rating:
        if d.cida_credit_rating == 1:
            designConf['cida_credit_rating'] = conf['cida_credit_rating_a']
        elif d.cida_credit_rating == 2:
            designConf['cida_credit_rating'] = conf['cida_credit_rating_b']
        elif d.cida_credit_rating == 3:
            designConf['cida_credit_rating'] = conf['cida_credit_rating_c']

    # 公号
    if d.wx_public_count:
        designConf['wx_public_count'] = d.wx_public_count * conf['wx_public_count']


    ## 统计影响力指数分值
    effectScore = 0
    for k, v in effectConf.items():
        effectScore += v


    ## 社会信誉
    creditConf = {
        'action_at_law_count': 0,
        'court_announcement_count': 0,
        'dishonest_person_count': 0,
        'person_subject_count': 0,
        'announcement_court_count': 0,
        'abnormal_operation_count': 0,
        'administrative_penalty_count': 0,
        'break_law_count': 0,
        'equity_pledged_count': 0,
        'chattel_mortgage_count': 0,
        'tax_notice_count': 0,
        'judicial_sale_count': 0,
        'tax_rating_count': 0,
        'credit_enter_extra': 0,
    }

    # 法律诉讼
    if d.action_at_law_count:
         creditConf['action_at_law_count'] = d.action_at_law_count * conf['action_at_law_count']
    # 法院公告
    if d.court_announcement_count:
         creditConf['court_announcement_count'] = d.court_announcement_count * conf['court_announcement_count']
    # 失信人
    if d.dishonest_person_count:
         creditConf['dishonest_person_count'] = d.dishonest_person_count * conf['dishonest_person_count']
    # 被执行人
    if d.person_subject_count:
         creditConf['person_subject_count'] = d.person_subject_count * conf['person_subject_count']
    # 开庭公告
    if d.announcement_court_count:
         creditConf['announcement_court_count'] = d.announcement_court_count * conf['announcement_court_count']
    # 经营异常
    if d.abnormal_operation_count:
         creditConf['abnormal_operation_count'] = d.abnormal_operation_count * conf['abnormal_operation_count']
    # 行政处罚
    if d.administrative_penalty_count:
         creditConf['administrative_penalty_count'] = d.administrative_penalty_count * conf['administrative_penalty_count']
    # 严重违法
    if d.break_law_count:
         creditConf['break_law_count'] = d.break_law_count * conf['break_law_count']
    # 股权出质
    if d.equity_pledged_count:
         creditConf['equity_pledged_count'] = d.equity_pledged_count * conf['equity_pledged_count']
    # 动产抵押
    if d.chattel_mortgage_count:
         creditConf['chattel_mortgage_count'] = d.chattel_mortgage_count * conf['chattel_mortgage_count']
    # 欠税公告
    if d.tax_notice_count:
         creditConf['tax_notice_count'] = d.tax_notice_count * conf['tax_notice_count']
    # 司法拍卖
    if d.judicial_sale_count:
         creditConf['judicial_sale_count'] = d.judicial_sale_count * conf['judicial_sale_count']
    # 税务评级
    if d.tax_rating_count:
        creditConf['tax_rating_count'] = d.tax_rating_count * conf['tax_rating_count']
    # 入驻加分
    if is_d3in:
        creditConf['credit_enter_extra'] = conf['credit_enter_extra']


    ## 统计社会信誉分值
    creditScore = 100
    for k, v in creditConf.items():
        creditScore += v


    ## 统计总分数
    # baseConf  businessConf  innovateConf  designConf  effectConf  creditConf
    totalScore = baseScore + businessScore + innovateScore + designScore + effectScore + creditScore

    row = {
        'mark': mark,
        'no': no,
        'number': str(d.number),
        'is_d3in': is_d3in,
        'base_score': baseScore,
        'base_group': baseConf,
        'business_score': businessScore,
        'business_group': businessConf,
        'innovate_score': innovateScore,
        'innovate_group': innovateConf,
        'design_score': designScore,
        'design_group': designConf,
        'effect_score': effectScore,
        'effect_group': effectConf,
        'credit_score': creditScore,
        'credit_group': creditConf,
        'total_score': totalScore,
    }

    recordQuery = {
        'mark': mark,
        'no': no,
        'number': str(d.number),
    }
    try:
        item = DesignRecord.objects(**recordQuery).first()
        if item:
            if item.deleted == 1:
                row['deleted'] = 0
            ok = item.update(**row)
        else:
            item = DesignRecord(**row)
            ok = item.save()
            
        if not ok:
            print("数据保存失败: %s" % str(ok))
            result['message'] = "数据保存失败: %s" % str(ok)
            return result
    except(Exception) as e:
        print("数据保存异常: %s" % str(e))
        result['message'] = "数据保存异常: %s" % str(e)
        return result
    
    print("stat success: %s" % d.number)
    print("------------------\n")
    result['data'] = item
    result['success'] = True
    return result

# 公司平均分统计--Core
@celery.task()
def average_stat_core(d, **options):
    result = {'success': False, 'message': ''}

    maxBase = options['max_base']
    maxBusiness = options['max_business']
    maxInnovate = options['max_innovate']
    maxDesign = options['max_design']
    maxEffect = options['max_effect']
    maxCredit = options['max_credit']
    f = options['f']
    bs = options['bs']
    bf = options['bf']

    designCompany = DesignCompany.objects(number=int(d.number)).fields(['_id', 'name', 'extra_base_score', 'extra_business_score', 'extra_innovate_score', 'extra_design_score', 'extra_effect_score', 'extra_credit_score']).first()
    if not designCompany:
        result['message'] = '公司不存在！'
        return result

    scoreQuery = {}
    aveScore = 0
    if maxBase:
        base_average = int(d.base_score / (maxBase.base_score + f) * 100 * bf + bs)
        if designCompany.extra_base_score:
            base_average += designCompany.extra_base_score
        scoreQuery['base_average'] = base_average
        aveScore += int(base_average * 0.1)
    if maxBusiness:
        business_average = int(d.business_score / (maxBusiness.business_score + f) * 100 * bf + bs)
        if designCompany.extra_business_score:
            business_average += designCompany.extra_business_score
        scoreQuery['business_average'] = business_average
        aveScore += int(business_average * 0.25)
    if maxInnovate:
        innovate_average = int(d.innovate_score / (maxInnovate.innovate_score + f) * 100 * bf + bs)
        if designCompany.extra_innovate_score:
            innovate_average += designCompany.extra_innovate_score
        scoreQuery['innovate_average'] = innovate_average
        aveScore += int(innovate_average * 0.25)
    if maxDesign:
        design_average = int(d.design_score / (maxDesign.design_score + f) * 100 * bf + bs)
        if designCompany.extra_design_score:
            design_average += designCompany.extra_design_score
        scoreQuery['design_average'] = design_average
        aveScore += int(design_average * 0.15)
    if maxEffect:
        effect_average = int(d.effect_score / (maxEffect.effect_score + f) * 100 * bf + bs)
        if designCompany.extra_effect_score:
            effect_average += designCompany.extra_effect_score
        scoreQuery['effect_average'] = effect_average
        aveScore += int(effect_average * 0.1)
    if maxCredit:
        credit_average = int(d.credit_score / (maxCredit.credit_score + f) * 100 * bf + bs)
        if designCompany.extra_credit_score:
            credit_average += designCompany.extra_credit_score
        scoreQuery['credit_average'] = credit_average
        aveScore += int(credit_average * 0.15)

    if not scoreQuery:
        print("current number:%s max score is 0\n" % d.number)
        result['message'] = 'current number max score is 0'
        return result

    scoreQuery['ave_score'] = aveScore
    ok = d.update(**scoreQuery)
    if not ok:
        print("更新失败~!")
        result['message'] = '更新失败!'
        return false

    result['success'] = True
    d.d3in_id = designCompany.d3ing_id
    result['data'] = d
    return result

# 排行平均分更新到铟果
@celery.task()
def ave_update_d3in(d3in_id, d):
    result = {'success': False, 'message': ''}
    if not d3in_id:
        result['message'] = 'd3in_id not exist!'
        return result

    url = "%s/%s" % (current_app.config['D3INGO_URL'], 'opalus/company/update')
    params = {
        'id': d3in_id,
        'ave_score': d['ave_score'],
        'base_average': d['base_average'],
        'credit_average': d['credit_average'],
        'business_average': d['business_average'],
        'design_average': d['design_average'],
        'effect_average': d['effect_average'],
        'innovate_average': d['innovate_average']
    }

    try:
        r = requests.put(url, params=params)
    except(Exception) as e:
        print(str(e))
        result['message'] = str(e)
        return result

    if not r:
        print('fetch design_case fail!!!')
        result['message'] = 'fetch design_case fail!!!'
        return result

    res = json.loads(r.text)
    if not 'meta' in res:
        print("data format error!")
        res['message'] = 'data format error!'
        return result
        
    if not res['meta']['status_code'] == 200:
        print(res['meta']['message'])
        result['message'] = res['meta']['message']
        return result

    result['success'] = True
    print("更新成功！")
    return result
