# 一、需求背景  
公司使用zabbix和prometheus同时进行监控，zabbix主要用于操作系统、应用、网络等监控，prometheus主要用于性能和中间件等监控。由于运维服务台基于zabbix，当前需要将prometheus告警内容接入到zabbix，使告警统一化、标准化。  
zabbix服务器IP：10.1.3.33  
prometheus服务器IP：10.1.3.60  
alertmanager服务器IP：10.1.3.60  
  

# 二、实现逻辑  
1、调用prometheus api（targets）接口获取所有监控主机。并形成json数据实现zabbix LLD（包括id、用户、环境和项目名）。  
2、监控项原型使用zabbix采集器，脚本使用zabbix_sender定时推送数据到zabbix服务器。  
3、调用alertmanager api接口获取告警（静默的除外），并且传id、告警级别进行匹配。  


# 三、实现功能  
1、可将代码微调部署在多个zabbix agent上，实现不同环境告警。  
2、实现了prometheus告警级别同步体现到zabbix上。  
3、两个脚本均会输出日志并进行监控，减少不标准prometheus设置、以及记录脚本运行失败的情况。  


# 四、实现要求  
1、consul注册主机ID、环境、用户和项目字段  
2、prometheus告警策略设置  
需要用到ID和severity，severity请设置成“一般告警”、“严重告警”，如果新增或修改级别名称需要修改代码。  
  - alert: ElasticsearchHealthyNodesmap10.1.5.3  
    expr: elasticsearch_cluster_health_number_of_nodes{environment="prod",id="prd-canal-10.1.5.3"} < 3  
    for: 30s  
    labels:  
      severity: "严重告警"  
    annotations:  
      message: "来源：prometheus\n项目：{{$labels.project}}\n环境：{{ $labels.environment }}\n服务：{{ $labels.service }}\n主机：{{ $labels.instance }}\n详情：Elasticsearch {{ $labels.id }} 集群在线节点数少于3个\n当前值：{{$value}}\n联系人：{{ $labels.user }}\n"  


# 五、discovery_targets.py脚本  
调用prometheus API接口获取所有主机。并形成JSON格式数据实现LLD（需要包括主机ID、环境、用户和项目数据）。  
1、脚本输出JSON数据格式如下  
{  
    "{#ID}": "prd-canal-10.1.5.3",  
    "{#ENV}": "prod",  
    "{#USER}": "姓名",  
    "{#PROJECT}": "map"  
}  

2、zabbix LLD配置  
挑一台zabbix agent设置即可，比如10.1.1.2  
（1）创建自动发现规则  
名称：Prometheus Host Discover  
类型：Zabbix客户端（主动方式）  
键值：discovery_targets  
更新间隔：300s  
资源周期不足：30d  

（2）监控项原型  
名称：{#PROJECT}项目，{#ENV}环境，ID为{#ID}  
类型：Zabbix采集器  
键值：prom_alerts[{#ID},warning]  
信息类型：字符  
应用集：Prometheus  

名称：{#PROJECT}项目，{#ENV}环境，ID为{#ID}  
类型：Zabbix采集器  
键值：prom_alerts[{#ID},critical]  
信息类型：字符  
应用集：Prometheus  

（3）触发器原型  
名称：{ITEM.VALUE1}；请联系{#USER}  
严重性：{10.1.1.2:prom_alerts[{#ID},warning].str(异常)}=1  

名称：{ITEM.VALUE1}；请联系{#USER}  
严重性：{10.1.1.2:prom_alerts[{#ID},critical].str(异常)}=1  

（4）脚本放在zabbix agent上  
cat userparameter_prometheus_host.conf  
UserParameter=discovery_targets,python3 /etc/zabbix/scripts/discovery_targets.py  
chmod 755 discovery_targets.py  


# 六、prometheus_to_zabbix.py脚本  
调用prometheus API接口获取所有主机后，再调用alertmanager api接口，确定告警的主机。将告警的主机id、severity和值使用zabbix_sender推送到zabbix采集器中（没告警的值发送“正常”字符，告警的值发送异常加alertmanager告警内容）。  

1、脚本内容  
chmod 755 prometheus_to_zabbix.py  

2、设置定时任务  
chmod 755 prometheus_to_zabbix.py  
crontab -l  
*/2 * * * * python3 /etc/zabbix/scripts/prometheus_to_zabbix.py   


# 七、监控脚本日志  
使用zabbix日志监控功能监控上述脚本输出的日志，看脚本运行过程中是否有报错。  
