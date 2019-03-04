#!/bin/bash
# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

# -rw-r--r-- root/root 302661020 2019-02-18 11:38 Image1.xz
# -rw-r--r-- root/root  40301128 2019-02-18 11:40 Image1.initrd
# -rw-r--r-- root/root        98 2019-02-18 11:40 Image1.append
# -rw-r--r-- root/root        45 2019-02-18 11:40 Image1.md5
# -rw-r--r-- root/root  40309036 2019-02-18 11:41 pxeboot.initrd.xz
# -rwxr-xr-x root/root   6643904 2019-02-18 11:40 pxeboot.kernel
# lrwxrwxrwx root/root         0 2019-02-18 11:40 Image1.kernel -> pxeboot.kernel

if [ -z "$1" ]; then
	echo "usage: $0 [name] <obs-image.tar.xz>"
	echo
	exit 1
fi

STATE="$1"
SDIR=images/$STATE
set -e
if [ -n "$2" ]; then
	if ! mkdir $SDIR; then
		echo "problem creating directory... please clean up first."
		echo
		exit 1
	fi
	cd $SDIR
	tar xfv $2
else
	if [ ! -d $SDIR ]; then
		echo "usage: $0 [name] <obs-image.tar.xz>"
		echo
		exit 1
	fi
	cd $SDIR
fi

NAME=`echo *.append`
if [ ! -e $NAME ]; then
	echo "something went wrong, $SDIR directory is not populated..."
	exit 1
fi

read KARG < $NAME
NAME=${NAME%.append}.xz
KARG=${KARG/rd.kiwi.install.image=http:\/\/example.com\/image.xz}

sed -e "s#@_KERNEL_ARG_@#$KARG#" -e "s#@_IMAGE_NAME_@#$NAME#" > host.tmpl << EOF
#!ipxe
set HTTP_BASE http://@SERVER_IP@:@SERVER_PORT@
set HTTP_STATE \${HTTP_BASE}/images/@state@
set KERNEL_ARG @_KERNEL_ARG_@
set IMAGE_NAME @_IMAGE_NAME_@
set KERNEL_LINE rd.kiwi.install.pass.bootparam rd.kiwi.install.image=\${HTTP_STATE}/\${IMAGE_NAME} \${KERNEL_ARG} BOOTIF=01-\${mac:hexhyp} razorurl=\${HTTP_BASE}/post-install?id=@id@

echo KIWIspray node @id@ template @state@
echo Installation node: \${HTTP_BASE}
echo Installation repo: \${HTTP_STATE}
echo Kernel args: \${KERNEL_ARG}
echo
echo kernel \${HTTP_STATE}/pxeboot.kernel
echo initrd \${HTTP_STATE}/pxeboot.initrd.xz
echo
prompt --key s --timeout 3000 hit 's' for the iPXE shell; continuing in 3 seconds && shell ||
kernel \${HTTP_STATE}/pxeboot.kernel \${KERNEL_LINE} || goto error
initrd \${HTTP_STATE}/pxeboot.initrd.xz || goto error
boot

:error
prompt --key s --timeout 60000 ERROR, hit 's' for the iPXE shell; reboot in 60 seconds && shell || reboot
EOF
