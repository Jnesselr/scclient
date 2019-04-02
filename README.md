# scclient
[![Build Status](https://travis-ci.org/Jnesselr/scclient.svg?branch=master)](https://travis-ci.org/Jnesselr/scclient)
[![Codacy Badge](https://api.codacy.com/project/badge/Coverage/47d670393ce9420d94c2df0c405efa60)](https://www.codacy.com/app/Jnesselr/scclient?utm_source=github.com&utm_medium=referral&utm_content=Jnesselr/scclient&utm_campaign=Badge_Coverage)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/47d670393ce9420d94c2df0c405efa60)](https://www.codacy.com/app/Jnesselr/scclient?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Jnesselr/scclient&amp;utm_campaign=Badge_Grade)
[![PyPI version](https://badge.fury.io/py/scclient.svg)](https://badge.fury.io/py/scclient)

## About this library
scclient is a python [SocketCluster](https://socketcluster.io/) client implementation. It aims to be a level 4 implementation, according to the [client guidelines](https://github.com/SocketCluster/client-drivers). The protocol is at least partially documented [here](https://github.com/SocketCluster/socketcluster/blob/master/socketcluster-protocol.md) and any missing pieces were figured out by analyzing the [existing python library](https://github.com/sacOO7/socketcluster-client-python).

## Goals

*  Comprehensive unit testing
*  [PEP 8](https://www.python.org/dev/peps/pep-0008/) style
*  Full SocketCluster client implementation
*  Non-blocking event driven architecture