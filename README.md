# rospy2: A ROS1-like interface for ROS2

Many people are still using ROS1 because it takes time to rewrite all your nodes for ROS2.

There is a [ROS1-ROS2 bridge](https://github.com/ros2/ros1_bridge) but it requires installing both ROS1 and ROS2 at the same time.

This provides a radically different solution: Your ROS1 code can work directly on the ROS2 network, as long as you aren't doing any crazy things.

All you need to do is install this package to your system:
```
sudo python3 setup.py install
```

And then in your node, change the line
```
import rospy
```

to
```
import rospy2 as rospy
```

You can even make nodes that work in both ROS1 and ROS2:
```
try:
    import rospy
except ImportError:
    import rospy2 as rospy
```

You should then be able to just run your node and it should work on ROS2. A test node that works in either ROS1 or ROS2 is provided:

ROS1:
```
source /opt/ros/noetic/setup.bash
./test_node.py
```

ROS2:
```
source /opt/ros/foxy/setup.bash
./test_node.py
```

# Status

## Supported

* Publishers

* Subscribers

* `rospy.Rate`, `rospy.Time`, `rospy.Time.now()`, `rospy.Duration`

* Parameters (in the same namespace as the node)

* ROS1-style positional constructors e.g. `String("hello")` or `Quaternion(1,2,3,4)` that ROS2 does not allow, for a few commonly-used types

## Not supported yet

* Parameters in other namespaces

* Service calls (supported but not tested)

## Caveats

* `seq` is not supported in ROS2 headers. rospy2 adds this back as a property, but it will always return 0. `seq` is deprecated even in ROS1 though I believe (?), so AFAIK you shouldn't be using it.

* Some message types changed slightly between ROS1 and ROS2. For example rosgraph_msgs/Log is now rcl_interfaces/Log and there is no longer a "topics" subfield. rospy2 aliases rosgraph_msgs/Log to rcl_interfaces/Log so it should still work as long as you aren't using `.topics`.

* There is no "parameter server" in ROS2, so ROS1 nodes that expect global parameters aren't going to work. Future functionality may allow rospy2 to fetch parameters from other nodes, but not from a global namespace.

* Since your callbacks will receive actual ROS2 messages, those messages that have numeric array fields (e.g. std_msgs/Int32MultiArray or sensor_msgs/Image)  will see those data fields as an array.array or numpy.ndarray instead of a Python list. This may trip up some code that expects a Python list. If your ROS1 code only accesses the data by index or constructs a numpy array as its first thing it does, it should theoretically not be an issue. If it *is* an issue, you can enable an experimental parameter that allows conversion to Python lists, ROS1 style:
```
    import rospy2 as rospy
    rospy.ARRAY_TO_LIST = True
```


