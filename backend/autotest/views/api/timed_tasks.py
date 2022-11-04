from flask import Blueprint, request

from autotest.services.api_services.timed_task import TimedTasksService
from autotest.utils.api import partner_success

bp = Blueprint('timed_tasks', __name__, url_prefix='/api/timedTasks')


@bp.route('/list', methods=['POST'])
def timed_tasks_list():
    """
    定时任务列表
    :return:
    """
    result = TimedTasksService.list(**request.json)
    return partner_success(data=result)


@bp.route('/saveOrUpdate', methods=['POST'])
def save_or_update():
    """
    新增，修改定时任务
    :return:
    """
    result = TimedTasksService.save_or_update(**request.json)
    return partner_success(data=result)


@bp.route('/taskSwitch', methods=['POST'])
def task_switch():
    """
    定时任务开关
    :return:
    """
    parsed_data = request.json
    task_id = parsed_data.get('id', None)
    result = TimedTasksService.task_switch(task_id)
    return partner_success(data=result)


@bp.route('/deleted', methods=['POST'])
def deleted_tasks():
    """
    删除任务
    :return:
    """
    parsed_data = request.json
    task_id = parsed_data.get('id', None)
    TimedTasksService.deleted(task_id)
    return partner_success()