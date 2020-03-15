![O3one](https://i.ibb.co/W3R6W7F/O3one.png)
 
**O3one MQ** is a simple, yet powerful messaging broker. It is based on lightweight ØMQ protocol.

## Installation
O3one MQ is bundled with a virtual env, production ready. 
To start the server with default config, you just need to launch :
```
C:\O3one> launch.bat
```
O3one MQ should start with the following header :
```

   oOO3 oo nn ee
 oOO    OO NN EE    O3one MQ 0.1 (0.1.0) 64bit WindowsPE
 oOO    OO NN EE    Pub: 5555    Sub: 5556
   oOO3 oo nn ee

```
If python yells something about missing dependencies, then you have to reconfigure the venv. To do so, you first need to activate it :
```
C:\O3one> venv\Scripts\activate.bat
```
Now you just need pip to install required dependencies with :
```
(venv) C:\O3one> pip install -r requirements.txt
```
and then launch O3one again. Please refer to [troubleshouting](#)  if you got any further issues.
## Getting started
There's a set of examples in folder `examples`. They all require O3one MQ to be started in order to work properly. To run an exemple, simply launch any `.bat` script, or invoque the pythons scripts in the venv.

 - **pub** is an example publisher. It will post any provided message in the default topic queue (nammed *o3*)
 - **sub** is a basic subscriber to the default topic. It will print any incoming message.
 - **pub_spam** is a stress-test publisher. It will post 50,000 messages and exit
 - **wsub** is a websocket subscriber, that will print any incoming websocket message. It is used in order to test the websocket bridge for subscribers.

## Using the dashboard 
 There's also a web UI to manage the server. It can be accessed at [http://127.0.0.1:9000/](http://127.0.0.1:9000/) (the default port it set to *9000*). It would present as the following image :
 ![Dashboard UI](https://i.ibb.co/Xx1nNNh/image.png)

The graph displays realtime messages count, and various informations about the backend state are presented.

 - **Health** is an health indictor about the server state. Default is **good**, meaning everything is ok but it can change to **degraded** is the server is receving a lot of request, **overloaded** if the server is over max load capacity, and **overflowed** if it can't keep track of incoming requests (the most critical state)
 - **Replication** tells wich replication is enabled for the backend. **MMAP** means that memory-mapped swap will be used as replication, and **SQL** means that every queries will be SQL-logged. Please refer to *Replication* for more details.
 - **Records** Counts processed records and storaged ones. Please note that MMAP can't hold an huge amount of messages, and will just rewrite itself with newer one, exmplaining the gap between numbers.
- **Uptime** just tells you how long the server has been online.
### Queue visualisation
Under the [O3one MQ](http://127.0.0.1:9000/) menu, choose [Dump](http://127.0.0.1:9000/dump). It will head you to the following page, where you can visualize up to 50 last messages.
![Queue visualisation](https://i.ibb.co/c8TN8X5/image.png)
## Replication
O3one MQ currently supports two differents replication technologies. 

**MMAP** is the short for *memory-map*. It's a very fast way to store a limited amount of data as a binary file, linked to RAM. It makes any program running on the same machine able to read in realtime the last queue elements. Enabled by default, it is meant as a "backup & restaure" solution for app crashes and reboot. Mmap can also be used as a dispatcher if we need many O3one MQ instances to run simultaneously. MMAP aren't lossless, they only keep track of lasts queue items, because it's a size-limitted buffer.

**SQL** means that every messages will be SQL-logged into a database. Currently, O3one MQ uses a *SQLite* database located in `db/o3mq.db`.  Although SQL is a lossless way to store informations, processing speed will be decreased by *~10* times when enabled.  It is recommanded to enable it only if you need a full track of everything and don't have an huge server load. 

## Configuration
### From a file
O3one MQ supports YAML configuration. The main file is called `O3one.yaml` under the `config` folder. 

Here's a simple configuration:
```yaml
dashboard_port: 9000
dashboard_enabled: yes
priority_enabled: no
db_path: ./db/
default_connect_timeout: 5
hostname: 127.0.0.1
log_path: ./logs/
port_pub: 5555
port_sub: 5556
mmap_enabled: yes
```
As the config file tells, every binded ports can be configured.

 - **dashboard_port** is the web Dashbord port
 - **hostname** is the host name. Change it to `0.0.0.0` to bind every interfaces.
 - **db_path** is the relative path for the database
 - **log_path** is the relative path for the logs
 - **mmap_enabled** enable or disable mmap support
 - **dashboard_enabled** enable or disable the dashboard
 - **persist_enabled** enable or disable SQL replication
> There's a little trick with names: **port_pub** is the port where subscribers will listen, as the names are thougts to be designed from a client point of view. And so, publishers will publish to **port_sub** and NOT *port_pub*. 

### From the code
O3one MQ is invoked in the `O3oneMQ.py` file. In the line *43*, you'll find the following code:
``` python
server = Backend({
        'persist_enabled': True,
        'mmap_enabled': False,
        'priority_enabled': False,
        'dashboard_enabled': True
    })
```
This configuration overrides the configuration file. Thoses arguments are meant for production when you don't need any configuration to be changed, like when you won't any sysadmin to enable SQL. THIS IS PROBABLY A BAD IDEA TO TWEAK IT.

## Developping with O3one MQ 
AS O3-MQ is ØMQ backed, it is definitely possible to connect it with various languages. Please refers to [the ZGuide](http://zguide.zeromq.org/page:all) for more details.
### In java
You'll need two dependencies in your code : `jeromq` and `jnacl`. Then, you could try the following example :
```java
try (ZContext context = new ZContext()) {  
  System.out.println("Subscribe to the server");  
  ZMQ.Socket subscriber = context.createSocket(SocketType.SUB);  
  // Connecting to the "Pub" port
  subscriber.connect("tcp://localhost:5555");  
  // Getting the default topic
  String sub = "o3";  
  subscriber.subscribe(sub.getBytes(ZMQ.CHARSET));  
  // Receiving some data & printing it
  String string = subscriber.recvStr(0).trim();  
  System.out.println(string);  
}
```
### In python
Please note that examples are wrote in python, and you could totaly re-use them.
#### Subscribing
```python
# common can be found under the "examples" folder
from common import *  
  
from o3mq.config import PORT_PUB  
from o3mq.backend import zmq  
from o3mq.pubsub import SubSocketType  
  
context = zmq.Context()  
socket = context.socket(SubSocketType.SUB.value)  
  
print("Waiting for message …")  
socket.connect("tcp://localhost:%s" % PORT_PUB)  
  
socket.setsockopt_string(SubSocketType.SUBSCRIBE.value, "o3")  
  
msg = socket.recv_string()  
print(msg)
```
#### Publishing
```python
# common can be found under the "examples" folder
from common import *  
  
from o3mq.config import PORT_SUB  
from o3mq.backend import zmq  
from o3mq.pubsub import SubSocketType  
  
context = zmq.Context()  
socket = context.socket(SubSocketType.REQ.value)  
socket.connect("tcp://localhost:%s" % PORT_SUB)  
  
topic = "o3"  
message = "Hello"  
priority = "5"  
socket.send_string("%s %s %s" % (topic, message, priority))
```

Client shall now display : `o3 Hello 5`

You can also ensure it have been posted on the Dashboard :

![enter image description here](https://i.ibb.co/znBqQYD/image.png)

## Final notes
> Why O3one ?

O3one began as a bad pun with "Ozone" because the project was originally nammed "o3" after a bad copy-paste. *O3* is the chemical formula for *Ozone* but "Ozone MQ" is far too anonymous. We needed something more fun, and decided to name it "O3one" in order to keep the original name. Also, O3one sounds like "0 free one" and also "031" so yeah it is definitely a super pun.  

> Why it is so slow ? 

O3one wasn't originally designed as a "professional" messaging broker, but more as an exeperiment. Altough it isn't perfect, it sill gave us good results for a homemade MQ. 
~~Note from author :  I originaly tried to install RabbitMQ but my connection sucks and I decided to create one from scratch instead of waiting for the Erlang download to end.~~

> Can you give me support with O3one MQ ? It does not work on my machine ?

No, but Uni can, Ganbatte ne ! 

![Uni shall protect you](https://66.media.tumblr.com/18e9654d35d470054de32789aa4107ea/5efa507109904d53-f1/s640x960/5b21a7f8a386683c792b497477f200c1e3669ab1.gif)

_PS: It works on my machine._
