# coding: utf-8
from app.extensions import celery
from app.helpers.common import force_int
from app.models.design_conf import DesignConf
from app.models.design_company import DesignCompany
from flask import current_app, jsonify
import requests
import json

# 统计奖项数量
@celery.task()
def company_stat(mark, no):

    conf = DesignConf.objects(mark=mark).first()
    if not conf:
        print("配置文件不存在！")
        return

    page = 1
    perPage = 100
    isEnd = False
    total = 0
    query = {}
    query['deleted'] = 0

    while not isEnd:
        data = DesignCompany.objects(**query).order_by('-created_at').paginate(page=page, per_page=perPage)
        if not data:
            print("get data is empty! \n")
            continue

        # 过滤数据
        for i, d in enumerate(data.items):
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
                'wx_public_count': 0,
            }
            # 入驻铟果
            if d.d3ing_id:
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
            # 公号
            if d.wx_public_count:
                baseConf['wx_public_count'] = d.wx_public_count * conf['wx_public_count']

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
                'tax_rating_count': 0,
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
            # 税务评级
            if d.tax_rating_count:
                businessConf['tax_rating_count'] = d.tax_rating_count * conf['tax_rating_count']

            ## 统计商业力指数分值
            businessScore = 0
            for k, v in businessConf.items():
                businessScore += v


            ## 创新力指数
            innovateConf = {
                'red_star_award_count': 0,
                'innovative_design_award_count': 0,
                'china_design_award_count': 0,
                'dia_award_count': 0,
                'if_award_count': 0,
                'red_dot_award_count': 0,
                'idea_award_count': 0,
                'trademark_count': 0,
                'patent_count': 0,
                'software_copyright_count': 0,
                'works_copyright_count': 0,
                'icp_count': 0,
            }

            # 红星奖
            if d.red_star_award_count:
                innovateConf['red_star_award_count'] = d.red_star_award_count * conf['red_star_award_count']
            # 红棉奖
            if d.innovative_design_award_count:
                innovateConf['innovative_design_award_count'] = d.innovative_design_award_count * conf['innovative_design_award_count']
            # 中国好设计奖
            if d.china_design_award_count:
                innovateConf['china_design_award_count'] = d.china_design_award_count * conf['china_design_award_count']
            # 中国设计智造大奖
            if d.dia_award_count:
                innovateConf['dia_award_count'] = d.dia_award_count * conf['dia_award_count']
            # if奖
            if d.if_award_count:
                innovateConf['if_award_count'] = d.if_award_count * conf['if_award_count']
            # 红点奖
            if d.red_dot_award_count:
                innovateConf['red_dot_award_count'] = d.red_dot_award_count * conf['red_dot_award_count']
            # IDEA工业设计奖
            if d.idea_award_count:
                innovateConf['idea_award_count'] = d.idea_award_count * conf['idea_award_count']
            # 商标
            if d.trademark_count:
                innovateConf['trademark_count'] = d.trademark_count * conf['trademark_count']
            # 专利
            if d.patent_count:
                innovateConf['patent_count'] = d.patent_count * conf['patent_count']
            # 软件著作权
            if d.software_copyright_count:
                innovateConf['software_copyright_count'] = d.software_copyright_count * conf['software_copyright_count']
            # 作品著作权
            if d.works_copyright_count:
                innovateConf['works_copyright_count'] = d.works_copyright_count * conf['works_copyright_count']
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
                designConf['d3in_case_count'] = d.d3in_case_count * conf['d3in_case_count']

            ## 统计设计力指数分值
            designScore = 0
            for k, v in designConf.items():
                designScore += v


            ## 影响力指数
            effectConf = {
                'is_high_tech': 0,
                'ty_score': 0,
                'ty_view_count': 0,
                'certification_count': 0,
                'cida_credit_rating': 0,
            }

            # 高新企业
            if d.is_high_tech:
                designConf['is_high_tech'] = conf['is_high_tech']
            # 天眼查分数
            if d.ty_score:
                designConf['ty_score'] = d.ty_score * conf['ty_score']
            # 天眼查浏览数
            if d.ty_view_count:
                designConf['ty_view_count'] = d.ty_view_count * conf['ty_view_count']
            # 资质证书
            if d.certification_count:
                designConf['certification_count'] = d.certification_count * conf['certification_count']

            # 工会认证
            if d.cida_credit_rating:
                if d.cida_credit_rating == 1:
                    designConf['cida_credit_rating'] = conf['cida_credit_rating_a']
                elif d.cida_credit_rating == 2:
                    designConf['cida_credit_rating'] = conf['cida_credit_rating_b']
                elif d.cida_credit_rating == 3:
                    designConf['cida_credit_rating'] = conf['cida_credit_rating_c']


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
            }

            # 法律诉讼
            if d.action_at_law_count:
                 designConf['action_at_law_count'] = d.action_at_law_count * conf['action_at_law_count']
            # 法院公告
            if d.court_announcement_count:
                 designConf['court_announcement_count'] = d.court_announcement_count * conf['court_announcement_count']
            # 失信人
            if d.dishonest_person_count:
                 designConf['dishonest_person_count'] = d.dishonest_person_count * conf['dishonest_person_count']
            # 被执行人
            if d.person_subject_count:
                 designConf['person_subject_count'] = d.person_subject_count * conf['person_subject_count']
            # 开庭公告
            if d.announcement_court_count:
                 designConf['announcement_court_count'] = d.announcement_court_count * conf['announcement_court_count']
            # 经营异常
            if d.abnormal_operation_count:
                 designConf['abnormal_operation_count'] = d.abnormal_operation_count * conf['abnormal_operation_count']
            # 行政处罚
            if d.administrative_penalty_count:
                 designConf['administrative_penalty_count'] = d.administrative_penalty_count * conf['administrative_penalty_count']
            # 严重违法
            if d.break_law_count:
                 designConf['break_law_count'] = d.break_law_count * conf['break_law_count']
            # 股权出质
            if d.equity_pledged_count:
                 designConf['equity_pledged_count'] = d.equity_pledged_count * conf['equity_pledged_count']
            # 动产抵押
            if d.chattel_mortgage_count:
                 designConf['chattel_mortgage_count'] = d.chattel_mortgage_count * conf['chattel_mortgage_count']
            # 欠税公告
            if d.tax_notice_count:
                 designConf['tax_notice_count'] = d.tax_notice_count * conf['tax_notice_count']
            # 司法拍卖
            if d.judicial_sale_count:
                 designConf['judicial_sale_count'] = d.judicial_sale_count * conf['judicial_sale_count']


            ## 统计社会信誉分值
            creditScore = 0
            for k, v in creditConf.items():
                creditScore += v


            ## 统计总分数
            # baseConf  businessConf  innovateConf  designConf  effectConf  creditConf
            totalScore = baseScore + businessScore + innovateScore + designScore + effectScore + creditScore


            row = {
                'mark': mark,
                'no': no,
                'number': d.number,
                'base_score': baseScore,
                'business_score': businessScore,
                'innovate_score': innovateScore,
                'design_score': designScore,
                'effect_score': effectScore,
                'credit_scroe': creditScore,
                'total_score': totalScore,
            }
            
            print(row)

            print("------------------\n")
            total += 1

        print("current page %s: \n" % page)
        page += 1
        if len(data.items) < perPage:
            isEnd = True

    print("is over execute count %s\n" % total)


