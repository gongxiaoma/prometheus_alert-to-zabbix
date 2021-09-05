# !/usr/bin/python
# -*- coding:utf-8 -*-
# author: gongxiaoma
# date： 2021-03-19
# version：1.0

import os
import logging
import logging.config
import platform
import requests

ALERTSAPI = "http://alertmanager服务器/api/v2"
PROMAPI = "http://prometheus服务器/api/v1"
LABELS = ("environment", "id", "user", "project")

standard_format = '[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%(filename)s:%(lineno)d]'\
                  '[%(levelname)s][%(message)s]'
simple_format = '[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d]%(message)s'

windows_logfile_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) + '\logs'
linux_logfile_dir = "/tmp/zabbix/logs"
logfile_name = "check_alert-error.log"


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
                                          'handlers': ['default', 'console'],
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


class CheckAlert(object):
    """
    读取prometheus api接口，
    传主机名参数、告警级别参数后匹配是否存在告警内存
    """

    """定义实例变量"""
    def __init__(self):
        self.ALERTSAPI = ALERTSAPI
        self.PROMAPI = PROMAPI
        self.LABELS = LABELS


    """访问targets api接口"""
    def access_targets_api(self):
        prom_tragets_url = self.PROMAPI + "/targets"
        result = requests.get(prom_tragets_url)
        targets_dict = result.json()
        targets_list = targets_dict['data']['activeTargets']
        return targets_list


    """使用zabbix-sender推送数据到监控项采集器中"""
    def sender_to_zabbix(self, id, severity, result):
        if severity == "一般告警":
            severity = "warning"
        else:
            severity = "critical"
        zabbix_sender_cmd = "/bin/zabbix_sender -z zabbix服务器 -p 10051 -s zabbix-agent主机 -k prom_alerts[%s,%s] -o \"%s\" &> /dev/null" % (id, severity, result)
        #print(zabbix_sender_cmd)
        restat_status = os.system(zabbix_sender_cmd)
        if restat_status != 0:
            error_msg = {'status': '失败', 'message': 'zabbix_sender发送数据失败：%s' % (zabbix_sender_cmd)}
            logger.error(error_msg)


    """获取alertsmanager告警内容，并传id和severity进行zabbix监控项检查"""
    def check_alerts(self, id, severity):
        try:
            prom_alerts_url = self.ALERTSAPI + "/alerts"
            param = {
                'silenced': 'false',
                'inhibited': 'true',
                'active': 'true'
            }
            result = requests.get(prom_alerts_url, params=param)
            alerts_list = result.json()
            result_list = []
            for i in alerts_list:
                if i['labels']['id'] == id and i['labels']['severity'] == severity:
                    alerts_content = i['annotations']['message']
                    alerts_result = alerts_content.split('\n')[5:7]
                    alerts_result = ", ".join(alerts_result)
                    result_list.append(alerts_result)
            result_desc = "【异常：Prometheus告警(" + str(len(result_list)) + ")】"
            result_list.insert(0, result_desc)
            if len(result_list) > 3:
                result_list.append("更多告警请查看：dashboard面板")
                result = "|||".join(result_list)
                self.sender_to_zabbix(id, severity, result)
            elif len(result_list) > 1:
                result = "|||".join(result_list)
                print(result)
                self.sender_to_zabbix(id, severity, result)
            else:
                self.sender_to_zabbix(id, severity, "正常")
        except Exception as e:
            error_msg = {'status': '失败', 'message': 'zabbix监控项检查失败：%s' % (e)}
            logger.error(error_msg)
            raise e


    """获取所有id，并调用检查告警方法"""
    def push_data_zabbix(self):
        targets_list = self.access_targets_api()
        data = []
        for i in targets_list:
            if all(k in i['labels'] for k in self.LABELS):
                if i['labels']['environment'] == 'prd' or i['labels']['environment'] == 'prod' or i['labels']['environment'] == 'produce':
                    data.append(i['labels']['id'])
        for i in data:
            self.check_alerts(i, "一般告警")
            self.check_alerts(i, "严重告警")



if __name__ == '__main__':
    run_log = RunLog(windows_logfile_dir, linux_logfile_dir, logfile_name)
    logger = run_log.logfile_write()
    check_alerts = CheckAlert()
    check_alerts.push_data_zabbix()