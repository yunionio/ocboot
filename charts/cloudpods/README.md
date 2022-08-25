# Cloudpods Helm Chart

使用 [Helm](https://helm.sh/) 安装 Cloudpods CMP 多云管理版本 [Cloudpods](https://cloudpods.org)

## 安装部署

安装 helm 工具请参考 https://helm.sh/docs/intro/install/ 。

### clone chart

Cloudpods Helm Chart 位于 https://github.com/yunionio/ocboot 仓库，使用以下命令下载到本地：

```bash
$ git clone https://github.com/yunionio/ocboot
$ cd charts/cloudpods
```

### 测试环境安装

测试环境安装方法如下，改方法会在 Kubernetes 集群里部署 mysql ，local-path-provisioner CSI 依赖插件，不需要连接集群之外的 mysql 。

```bash
$ helm install --name-template default --namespace onecloud --debug  . -f values-dev.yaml  --create-namespace
```

### 生产环境安装

之前部署的方法仅限测试使用，因为依赖少，安装快，但如果用于生产环境，请根据需求修改 ./values-prod.yaml 里面的参数，然后使用该文件创建 Helm Release 。

建议需要修改的地方如下：

```diff
 localPathCSI:
+  # 根据 k8s 集群的 CSI 部署情况，选择是否要部署默认的 local-path CSI
+  # 如果 k8s 集群已经有稳定的 CSI ，就可以设置这个值为 false ，不部署该组件
   enabled: true
   helperPod:
     image: registry.cn-beijing.aliyuncs.com/yunionio/busybox:1.35.0
@@ -60,11 +62,16 @@ localPathCSI:

 cluster:
   mysql:
+    # 外部 mysql 地址
     host: 1.2.3.4
+    # 外部 mysql 端口
     port: 3306
+    # 外部 mysql 用户，需要用具备 root 权限的用户，因为 cloudpods operator 会为其他服务创建数据库用户
     user: root
+    # 外部 mysql 密码
     password: your-db-password
     statefulset:
+      # 生产环境部署这里需要设置成 false ，不然会在 k8s 集群里面部署一个 mysql ，然后连接使用这个 statefulset mysql
       enabled: false
       image:
         repository: "registry.cn-beijing.aliyuncs.com/yunionio/mysql"
@@ -91,15 +98,20 @@ cluster:
   # imageRepository defines default image registry
   imageRepository: registry.cn-beijing.aliyuncs.com/yunion
   # publicEndpoint is upstream ingress virtual ip address or DNS domain
+  # 集群外部可访问的域名或者 ip 地址
   publicEndpoint: foo.bar.com
   # edition choose from:
   # - ce: community edition
   # - ee: enterprise edition
+  # 选择部署 ce(开源) 或者 ee(企业) 版本
   edition: ce
   # storageClass for stateful component
+  # 有状态服务使用的 storageClass，如果不设置就会使用 local-path CSI
+  # 这个可根据 k8s 集群情况自行调节
   storageClass: ""
   ansibleserver:
     service:
+      # 指定服务暴露的 nodePort，如果和集群已有服务冲突，可以修改
       nodePort: 30890
   apiGateway:
     apiService:
@@ -193,6 +205,7 @@ cluster:
     service:
       nodePort: 30889

+# 设置 ingress
 ingress:
   enabled: true
   className: ""
```

修改完 values-prod.yaml 文件后，用以下命令部署：

```bash
$ helm install --name-template default --namespace onecloud . -f values-prod.yaml  --create-namespace
```

## 创建默认管理用户

### 进入 climc 命令行 pod

如果是部署的 ce(社区开源版本)，需要使用平台的命令行工具创建默认用户，进行相关操作，对应命令如下，首先是进入 climc pod 容器：

```bash
# 进入 climc pod
$ kubectl exec -ti -n onecloud $(kubectl get pods -n onecloud | grep climc | awk '{print $1}') sh
/ #
```

### 创建用户

在 climc pod 里面创建 admin 用户，命令如下：

```bash
# 创建 admin 用户，设置密码为 admin@123 ，根据需求自己调整
[in-climc-pods]$ climc user-create --password 'admin@123' --enabled admin

# 允许 web 登陆
[in-climc-pods]$ climc user-update --allow-web-console admin

# 将 admin 用户加入 system project 赋予管理员权限
[in-climc-pods]$ climc project-add-user system admin admin
```

## 访问前端

根据创建的 ingress 访问平台暴露出来的前端，通过下面的命令查看 ingress ：

```bash
# 我测试的集群 ingress 信息如下，不同的 k8s 集群根据 ingress 插件的实现各有不同
$ kubectl get ingresses -n onecloud
NAME                    HOSTS   ADDRESS                 PORTS     AGE
default-cloudpods-web   *       10.127.100.207          80, 443   7h52m
```

使用浏览器访问 https://10.127.100.207 即可访问平台前端，然后使用之前创建的 admin 用户登陆。

## 升级

升级可以通过修改对应的 values yaml 文件，然后进行升级配置，比如发现 cluster.regionServer.service.nodePort 的 30888 端口出现了占用冲突，要修改成其它端口 30001，就修改 values-prod.yaml 里面对应的值：

```diff
--- a/charts/cloudpods/values-prod.yaml
+++ b/charts/cloudpods/values-prod.yaml
@@ -170,7 +170,7 @@ cluster:
       nodePort: 30885
   regionServer:
     service:
-      nodePort: 30888
+      nodePort: 30001
   report:
     service:
       nodePort: 30967
```

然后使用 helm upgrade 命令升级：

```bash
$ helm upgrade -n onecloud default . -f values-prod.yaml
```

再查看 onecloudcluster 资源，会发现对应的 spec.regionServer.service.nodePort 变成了 30001，对应的 service nodePort 也会发生变化：

```bash
# 查看 regionServer 在 onecloudcluster 里面的属性
$ kubectl get oc -n onecloud default-cloudpods -o yaml | grep -A 15 regionServer
  regionServer:
    affinity: {}
    disable: false
    dnsDomain: cloud.onecloud.io
    dnsServer: 10.127.100.207
    image: registry.cn-beijing.aliyuncs.com/yunion/region:v3.9.1
    imagePullPolicy: IfNotPresent
    limits:
      cpu: "1.333333"
      memory: 2045Mi
    replicas: 1
    requests:
      cpu: 10m
      memory: 10Mi
    service:
      nodePort: 30001

# 查看 default-cloudpods-region service 的 nodePort
$ kubectl get svc -n onecloud | grep region
default-cloudpods-region          NodePort    10.110.105.228   <none>        30001:30001/TCP                   7h30m
```

查看之前变更的 cluster.regionServer.service.nodePort 是否在平台的 endpoint 里面发生了变化：

```bash
# 使用 climc pod 指定 endpoint-list 命令查看
$ kubectl exec -ti -n onecloud $(kubectl get pods -n onecloud | grep climc | awk '{print $1}') -- climc endpoint-list --search compute
+----------------------------------+-----------+----------------------------------+----------------------------------------+-----------+---------+
|                ID                | Region_ID |            Service_ID            |                  URL                   | Interface | Enabled |
+----------------------------------+-----------+----------------------------------+----------------------------------------+-----------+---------+
| c88e03490c2543a987d86d733b918a2d | region0   | a9abfdd204e9487c8c4d6d85defbfaef | https://10.127.100.207:30001           | public    | true    |
| a04e161ee71346ac88ddd04fcebfe5ce | region0   | a9abfdd204e9487c8c4d6d85defbfaef | https://default-cloudpods-region:30001 | internal  | true    |
+----------------------------------+-----------+----------------------------------+----------------------------------------+-----------+---------+
***  Total: 2 Pages: 1 Limit: 20 Offset: 0 Page: 1  ***
```

## 删除

```bash
$ helm delete -n onecloud default
```
