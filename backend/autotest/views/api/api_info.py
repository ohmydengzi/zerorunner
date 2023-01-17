import json

from flask import Blueprint, request
from loguru import logger

from autotest.exc import codes
from autotest.services.api_services.api_info import ApiInfoService
from autotest.tasks.case import async_run_case, run_timed_task
from autotest.utils.api import partner_success

bp = Blueprint('api_info', __name__, url_prefix='/api/apiInfo')


@bp.route('/list', methods=['POST'])
def case_list():
    """
    获取用例列表
    :return:
    """
    result = ApiInfoService.list(**request.json)
    return partner_success(data=result)


@bp.route('/getTestCaseInfo', methods=['POST'])
def get_case_info():
    """
    获取用例信息
    :return:
    """
    case_info = ApiInfoService.detail(**request.json)
    return partner_success(case_info)


@bp.route('/saveOrUpdate', methods=['POST'])
def save_or_update():
    """
    更新保存测试用例
    :return:
    """
    parsed_data = request.json
    case_info = ApiInfoService.save_or_update(**parsed_data)
    return partner_success(case_info.id)


@bp.route('/setCaseStatus', methods=['POST'])
def set_case_status():
    """
    用例失效生效
    :return:
    """
    parsed_data = request.json
    ApiInfoService.set_api_status(**parsed_data)
    return partner_success()


@bp.route('/deleted', methods=['POST'])
def deleted():
    """
    删除用例
    :return:
    """
    parsed_data = request.json
    c_id = parsed_data.get('id', None)
    ApiInfoService.deleted(c_id)
    return partner_success()


@bp.route('/run', methods=['POST'])
def run_test():
    """
    运行用例
    :return:
    """
    parsed_data = request.json
    if parsed_data.get('run_type', None) == 20:
        logger.info('异步执行用例 ~')
        async_run_case.delay(**parsed_data)
        return partner_success(code=codes.PARTNER_CODE_OK, msg='用例执行中，请稍后查看报告即可,默认模块名称命名报告')
    else:
        summary = ApiInfoService.run(**parsed_data)  # 初始化校验，避免生成用例是出错
        return partner_success(data=summary)


@bp.route('/debugApi', methods=['POST'])
def debug_api():
    """
    调试用例
    :return:
    """
    data = ApiInfoService.debug_testcase(**request.json)
    return partner_success(data)


@bp.route('/testRunCase', methods=['POST'])
def test_run_case():
    """
    测试运行用例
    :return:
    """
    data = run_timed_task(**request.json)
    return partner_success(data)


@bp.route('/postman2case', methods=['POST'])
def postman2case():
    """
    postman 文件转用例
    :return:
    """
    postman_file = request.files.get('file', None)
    if not postman_file:
        return partner_success(code=codes.PARTNER_CODE_FAIL, msg='请选择导入的postman，json文件！')
    if postman_file.filename.split('.')[-1] != 'json':
        return partner_success(code=codes.PARTNER_CODE_FAIL, msg='请选择json文件导入！')
    json_body = json.load(postman_file)
    data = ApiInfoService.postman2api(json_body, **request.form)
    return partner_success(data)