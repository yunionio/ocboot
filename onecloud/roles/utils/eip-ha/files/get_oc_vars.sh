#!/usr/bin/bash

source <(/opt/yunion/bin/ocadm cluster rcadmin)
env | grep OS_ |sed -e 's#OS_REGION_NAME#oc_region#' \
					-e 's#OS_AUTH_URL#oc_auth_url#' 	\
					-e 's#OS_USERNAME#oc_admin_user#'	\
					-e 's#OS_PASSWORD#oc_admin_password#'	\
					-e 's#OS_PROJECT_NAME#oc_admin_project#' \
					-e 's#=#: "#' \
					-e 's#$#"#'	\
						|grep '^oc_' > /tmp/oc_vars
