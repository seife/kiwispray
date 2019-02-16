# KIWIspray

A tool for easily deploying KIWI images via PXE

## Purpose

Images built with [KIWI] (https://opensource.suse.com/kiwi/) already contain everything needed to deploy via PXE boot (at least the "oem" type). To deploy a machine with such an image, you need to:

   * boot the included `pxeboot.kernel` and `pxeboot.initrd.xz` with the options given in `<imagename>.append`
   * give the location (URL) of `<imagename.xz>` as `rd.kiwi.install.image=` on the kernel command line

This tool aims to automate this:

   * dynamically configure the boot mode
   * remember the state of a machine, so that after deployment it will no longer boot (and reinstall) the PXE image
   * allow to attach some metadata to a machine
   * provide a template based simple first-boot configuration

For PXE boot, the [iPXE] (https://ipxe.org) open source boot firmware is used.
For DHCP / tftp services, [dnsmasq] (http://www.thekelleys.org.uk/dnsmasq/doc.html) is used.

## Description of the boot sequence

   * machine's firmware (BIOS or UEFI) issues a bootp request
   * dnsmasq answers with an IP address and filename `undionly.kpxe` (BIOS) or `snponly.efi` (UEFI)
   * machine's firmware gets the filename via tftp from dnsmasq and executes it
   * iPXE takes over, asks again with BOOTP
   * dnsmasq answers with an IP address and filename `http://<my_ip>:<ks_port>/bootstrap.ipxe`
   * iPXE downloads `bootstrap.ipxe`, which is an iPXE script, and executes it
   * `bootstrap.ipxe` determines the MAC addresses of the first 8 Network cards, the DMI serial number and the DMI UUID of the machine and sends a request to `http://<my_ip>:<ks_port>/bootstrap?net0=<MAC0>&net1=<MAC0>&...&serial=<SERIAL>&uuid=<UUID>`
   * the `/bootstrap` path is handled by KIWIspray and dynamically generates a iPXE script, depending on the machine state:
   * machine is not yet known, state "new":
      * the script echos some information on the console, then waits for 30 minutes and reboots
   * machine is known and in state "finished":
      * the script tells ipxe to exit which in turn causes the next boot option to be tried (=> boot from disk)
   * machine is in another, arbitrarily named state:
      * configuration from directory `images/<state/` is applied, usually instructions how to boot the image in there

## Transition between states

To start the installation of "image1", the machine needs to be put into state "image1". This can be done with the script `edit-host.py`. The next boot of this machine will then apply this state

To transition a machine to the "finished" state after installing, the URL `http://<my_ip>:<ks_port>/finish?id=<ID>` needs to be fetched with the proper ID. The ID can be found with `edit-host.py -l`.

To automate this transition to finished, a post-install script is provided by the URL `http://<my_ip>:<ks_port>/post-install?id=<ID>`. This script gets rendered from the template `post_install.tmpl`, which is searched in the image's directory or, if not present there, in `templates/`.

You need to implement some way in your image to get the location of this post-install URL during installation, then fetch and execute it. We implemented this by appending `razorurl=<POST_INSTALL_URL>` to the kernel command line.

## File System Layout

```
.
├── ks.py
├── edit-host.py
├── install-new-image.sh
├── known_hosts.json
├── images
│   ├── image1
│   │   ├── image1.append
│   │   ├── image1.initrd
│   │   ├── image1.kernel -> pxeboot.kernel
│   │   ├── image1.md5
│   │   ├── image1.xz
│   │   ├── host.tmpl
│   │   ├── pxeboot.initrd.xz
│   │   └── pxeboot.kernel
│   ├── image2
│   │   ├── image2.append
│   │   ├── image2.initrd
│   │   └── <...>
│   └── <...>
├── KS
│   ├── handler.py
│   └── helpers.py
└── templates
    ├── bootstrap.ipxe
    ├── finished.tmpl
    ├── known_host.tmpl
    ├── new_host.tmpl
    ├── new.tmpl -> new_host.tmpl
    └── post_install.tmpl
```
