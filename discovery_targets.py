# !/usr/bin/python
# -*- coding:utf-8 -*-
# author: gongxiaoma
# date： 2021-03-19
# version：1.0

import os
import json
import logging
import logging.config
import platform
import requests

PROMAPI = "http://prometheus服务器/api/v1"
LABELS = ("environment", "id", "user", "project")

standard_format = '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%(filename)s:%(lineno)d]'\
                  '[%(levelname)s][%(message)s]'
simple_format = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%(message)s'

windows_logfile_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) + '\logs'
linux_logfile_dir = "/tmp/zabbix/logs"
logfile_name = "prom_targets_to_zabbix_json-error.log"


class RunLog(object):
    """
    日志类，
    将日志记录到指定文件中
    """

    """定义实例变量"""
    def __init__(self, windows_logfile_dir, linux_logfile_dir, logfile_name):
        self.windows_logfile_dir = windows_logfile_dir
        self.linux_logfile_dir = linux_logfile_dir
        self.logfile_name = logfile_name


    """定义日志路径"""
    def logfile_path(self):
        sys = platform.system()
        if sys == "Windows":
            logfile_dir = self.windows_logfile_dir
        else:
            logfile_dir = self.linux_logfile_dir
        if not os.path.isdir(logfile_dir):
            os.makedirs(logfile_dir)
        logfile_path = os.path.join(logfile_dir, self.logfile_name)
        return logfile_path


    """定义logging日志字典"""
    def logging_dict(self):
        logfile_path = self.logfile_path()
        logging_config_dict = {
                           'version': 1,
                           'disable_existing_loggers': False,
                           'formatters': {
                               'standard': {
                                   'format': standard_format
                               },
                               'simple': {
                                   'format': simple_format
                               },
                           },
                           'filters': {},
                           'handlers': {
                               # 打印DEBUG级别日志到终端屏幕
                               'console': {
                                   'level': 'DEBUG',
                                   'class': 'logging.StreamHandler',
                                   'formatter': 'simple'
                               },
                               # 打印DEBUG级别日志到文件
                               'default': {
                                   'level': 'DEBUG',
                                   'class': 'logging.handlers.RotatingFileHandler',
                                   'formatter': 'standard',
                                   'filename': logfile_path,
                               'maxBytes': 1024 * 1024 * 5,
                               'backupCount': 5,
                               'encoding': 'utf-8',
                           },
                       },
                       'loggers': {
                                      # logging.getLogger(__name__)的logger配置，handlers可以根据自己情况设置
                                      '': {
                                          'handlers': ['default'],
                                          'level': 'INFO',
                                          'propagate': True,
                                      },
                                  },
        }
        return logging_config_dict


    """日志写入方法"""
    def logfile_write(self):
        logging_dict = self.logging_dict()
        logging.config.dictConfig(logging_dict)
        logger = logging.getLogger(__name__)
        return logger


class DiscoveryJson(object):
    """
    读取prometheus api接口，
    将非生产环境服务器、环境、用户和项目信息形成json传给zabbix自动发现规则
    """

    """定义实例变量"""
    def __init__(self):
        self.PROMAPI = PROMAPI
        self.LABELS = LABELS


    """检查字段静态方法"""
    @staticmethod
    def check_fields(i, field):
        instance = i['labels']['instance']
        error_msg = {'status': '失败', 'message': '以下instance无%s字段，请完善：%s' % (field, instance)}
        logging.error(error_msg)


    """访问targets api接口"""
    def access_targets_api(self):
        prom_tragets_url = self.PROMAPI + "/targets"
        result = requests.get(prom_tragets_url)
        targets_dict = result.json()
        targets_list = targets_dict['data']['activeTargets']
        return targets_list


    """获取自动发现规则json数据"""
    def get_prom_targets(self):
        try:
            targets_list = self.access_targets_api()
            data = []
            for i in targets_list:
                if all(k in i['labels'] for k in self.LABELS):
                    if i['labels']['environment'] == 'prd' or i['labels']['environment'] == 'prod' or i['labels']['environment'] == 'produce':
                        data += [{'{#ID}': i['labels']['id'], '{#ENV}': i['labels']['environment'], '{#USER}': i['labels']['user'], '{#PROJECT}': i['labels']['project']}]
                elif 'user' not in i['labels']:
                    self.check_fields(i, 'user')
                elif 'id' not in i['labels']:
                    self.check_fields(i, 'id')
                elif 'environment' not in i['labels']:
                    self.check_fields(i, 'environment')
                elif 'project' not in i['labels']:
                    self.check_fields(i, 'project')
            print(json.dumps({'data': data}, ensure_ascii=False, indent=4))
        except Exception as e:
            error_msg = {'status': '失败', 'message': '输出json数据失败：%s' % (e)}
            logger.error(error_msg)
            raise e

if __name__ == '__main__':
    run_log = RunLog(windows_logfile_dir, linux_logfile_dir, logfile_name)
    logger = run_log.logfile_write()
    zabbix_discovery = DiscoveryJson()
    zabbix_discovery.get_prom_targets()
