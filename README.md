EMC Plugins for ClusterHQ/Flocker
======================

These are plugin drivers for the [Flocker](https://clusterhq.com/) project which delivers Fast, local, persistent storage for Docker containers, Multi-host container management, Database migrations, and Flexible shared storage (SAN, NAS or block) for Docker when you want it.

## Description
Flocker can help orchestrate and provision storage to your clustered docker container microservices applications. Use cases include -->
- Seamlessly Running Stateful Microservices
  - Run Databases in Containers
        - MongoDB, Cassandra, Postgres, MySQL, and more!
- Generally orchestrate and schedule your container applications across a cluster that optionally provides flexible shared storage when you need it.
- Use it with [Docker Native Extensions](https://github.com/ClusterHQ/flocker-docker-plugin)

Drivers
-------
- ScaleIO
- XtremIO
- VMAX
- CorpHD
- VNX
- Unity


Driver Download
---------
Please refer the repository sub-directories above for information relating to reach driver.

The CorpHD driver is uploaded as submodule. For downloading CorpHD driver kindly run following two extra commands

```
git submodule init
git submodule update
```

Demo
----
There are `Vagrantfiles` for both XtremIO and ScaleIO to help demonstrate the integration.  Check the `/demo` directory for details.


Licensing
---------
**EMC will not provide legal guidance on which open source license should be used in projects. We do expect that all projects and contributions will have a valid open source license, or align to the appropriate license for the project/contribution**

Copyright [2015] [EMC Corporation]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Support
-------
Please file bugs and issues at the Github issues page. For more general discussions you can contact the Flocker team at <a href="https://groups.google.com/forum/#!forum/flocker-users">Google Groups</a> or tagged with **EMC** on <a href="https://stackoverflow.com">Stackoverflow.com</a>. The code and documentation are released with no warranties or SLAs and are intended to be supported through a community driven process.
