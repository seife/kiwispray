#!/bin/bash
# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING
#
# This imports a kiwi built live iso, to be booted via pxe.
# note: it is absolutely essential that the iso is built with
# <type ... flags="dmsquash"...>, or this will not work.
#
# A tested image is built in the openSUSE Build Service:
# https://build.opensuse.org/package/show/home:seife:kiwitest/SLES_15SP0_ks-config-iso
# https://download.opensuse.org/repositories/home:/seife:/kiwitest/images/iso/

if [ -z "$2" ]; then
	echo "usage: $0 [name] [obs-live.iso]"
	echo
	exit 1
fi
NAME=${2##*/}

STATE="$1"
SDIR=images/$STATE
set -e
type 7z > /dev/null

if [ ! -d $DIR ] && ! mkdir $SDIR; then
	echo "problem creating directory... please clean up first."
	echo
	exit 1
fi
cd $SDIR
cp -p "$2" .

7z e "$NAME" boot/x86_64/loader/{linux,initrd}

sed -e "s#@_IMAGE_NAME_@#$NAME#" > host.tmpl << EOF
#!ipxe
set HTTP_BASE http://@SERVER_IP@:@SERVER_PORT@
set HTTP_STATE \${HTTP_BASE}/images/@state@
set KERNEL_ARG net.ifnames=1 video=800x600 root=live:\${HTTP_STATE}/@_IMAGE_NAME_@
set @_IMAGE_NAME_@
set KERNEL_LINE \${KERNEL_ARG} BOOTIF=01-\${mac:hexhyp} razorurl=\${HTTP_BASE}/post-install?id=@id@&bootid=@bootid@

echo KIWIspray node @id@ template @state@
echo Installation node: \${HTTP_BASE}
echo Installation repo: \${HTTP_STATE}
echo Kernel args: \${KERNEL_ARG}
echo
echo kernel \${HTTP_STATE}/linux
echo initrd \${HTTP_STATE}/initrd
echo
prompt --key s --timeout 3000 hit 's' for the iPXE shell; continuing in 3 seconds && shell ||
kernel \${HTTP_STATE}/linux \${KERNEL_LINE} || goto error
initrd \${HTTP_STATE}/initrd || goto error
boot

:error
prompt --key s --timeout 120000 ERROR, hit 's' for the iPXE shell; reboot in 120 seconds && shell || reboot
EOF
