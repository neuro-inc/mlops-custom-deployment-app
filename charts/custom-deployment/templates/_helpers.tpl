{{/*
Expand the name of the chart.
*/}}
{{- define "custom-deployment.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "custom-deployment.fullname" -}}
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

{{- define "custom-deployment.dockerconfig-secret-name" -}}
{{- (include "custom-deployment.fullname" .) }}-dockerconfig
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "custom-deployment.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "custom-deployment.labels" -}}
application: {{ .Values.labels.application }}
helm.sh/chart: {{ include "custom-deployment.chart" . }}
{{ include "custom-deployment.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "custom-deployment.selectorLabels" -}}
app.kubernetes.io/name: {{ include "custom-deployment.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "custom-deployment.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "custom-deployment.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Pod-specific labels
*/}}
{{- define "custom-deployment.apoloPodLabels" -}}
platform.apolo.us/preset: {{ .Values.preset_name }}
platform.apolo.us/component: app
platform.apolo.us/org: {{ .Values.org }}
platform.apolo.us/projectorg: {{ .Values.project }}
{{- end }}

{{- define "custom-deployment.storageAnnotations" -}}
{{- if .Values.storageMounts }}
platform.apolo.us/inject-storage: {{ .Values.storageMounts | toJson }}
{{- end }}
{{- end }}
