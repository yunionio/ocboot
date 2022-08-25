{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "cloudpods.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cloudpods.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "cloudpods.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "cloudpods.labels" -}}
helm.sh/chart: {{ include "cloudpods.chart" . }}
{{ include "cloudpods.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "cloudpods.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cloudpods.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "cloudpods.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "cloudpods.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return the appropriate apiVersion for statefulset
*/}}
{{- define "statefulset.apiVersion" -}}
{{- if semverCompare "<1.17-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "apps/v1beta2" -}}
{{- else -}}
{{- print "apps/v1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for cronjob APIs.
*/}}
{{- define "cronjob.apiVersion" -}}
{{- if semverCompare "< 1.8-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "batch/v2alpha1" }}
{{- else if semverCompare ">=1.8-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "batch/v1beta1" }}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for ingress.
*/}}
{{- define "ingress.apiVersion" -}}
{{- if semverCompare "<1.14-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "extensions/v1beta1" -}}
{{- else -}}
{{- print "networking.k8s.io/v1beta1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the cluster storageClass
*/}}
{{- define "cloudpods.cluster.storageClass" -}}
{{- if .Values.cluster.storageClass -}}
{{- print .Values.cluster.storageClass -}}
{{- else if .Values.localPathCSI.enabled  -}}
{{- print "local-path" -}}
{{- else -}}
{{- fail ".Values.cluster.storageClass required" -}}
{{- end -}}
{{- end -}}

{{/*
Return the local-path-csi image
*/}}
{{- define "cloudpods.localPathCSI.image" -}}
{{- if semverCompare "<1.20-0" .Capabilities.KubeVersion.GitVersion -}}
{{- print "registry.cn-beijing.aliyuncs.com/yunionio/local-path-provisioner:v0.0.11" -}}
{{- else -}}
{{- print "registry.cn-beijing.aliyuncs.com/yunionio/local-path-provisioner:v0.0.22" -}}
{{- end -}}
{{- end -}}

{{/*
Return operator name
*/}}
{{- define "cloudpods.operator.fullname" -}}
{{- printf "%s-operator" (include "cloudpods.fullname" .) -}}
{{- end -}}

{{/*
Return web name
*/}}
{{- define "cloudpods.web.fullname" -}}
{{- printf "%s-web" (include "cloudpods.fullname" .) -}}
{{- end -}}

{{/*
Return web's certs name
*/}}
{{- define "cloudpods.web.certs.fullname" -}}
{{- printf "%s-certs" (include "cloudpods.fullname" .) -}}
{{- end -}}

{{/*
Return mysql name
*/}}
{{- define "cloudpods.mysql.fullname" -}}
{{- printf "%s-mysql" (include "cloudpods.fullname" .) -}}
{{- end -}}

{{/*
Return the mysql host
*/}}
{{- define "cloudpods.cluster.mysql.host" -}}
{{- if .Values.cluster.mysql.statefulset.enabled -}}
{{- printf "%s-mysql-svc" (include "cloudpods.fullname" .) -}}
{{- else -}}
{{- print .Values.cluster.mysql.host -}}
{{- end -}}
{{- end -}}
