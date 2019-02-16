# Templates

These are very simple templates for various files returned via the web API.

These templates are handled by very simple search-and-replace routines, in general it's like

```
Hello, this is host @HOST@ in state @state@
```

The "variables" that can be replaced are:

All the mandatory from the `known_hosts.json` file which are:
   * `id`: the number identifying the host
   * `hostname`: the given hostname
   * `state`: the current state of the machine, "new" for newly discovered machines, "finished" for already installed or anothe state set manually in order to install an image
   * `macs`: a space-separated list of MAC addresses
   * `serial`: the content of the `product_serial` field of DMI machine data
   * `uuid`: the contend of the `product_uuid` DMI field
If you have set metadata on a host, the contents of the metadata hash are also available in the form `metadata.<key>`.
Example: Consider a host entry with the following metadata entry:

```
   "metadata": {
       "fqdn": "my.host.fqdn",
       "location": "Rack-Number 1"
   },
```

Then you can use `@metadata.fqdn@` and `@metadata.location@` in your template.
