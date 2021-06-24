#!/usr/bin/env python3

import hashlib
import os
import rclpy
import sys
import time
import types
import threading
from .constants import *

rclpy.init(args = sys.argv)

# Variables starting with an underscore are stored ROS2 objects and are not
# intended to be used directly.
# All normally-named functions/classes/methods are designed to function exactly
# as per their ROS1 namesake.

_node = None
_logger = None
_clock = None
_thread_spin = None
_wait_for_message_release = False

def get_param(param_name, default_value = None):
    global _node
    return _node.get_parameter_or(param_name, default_value)._value

def init_node(node_name, anonymous=False, log_level=INFO, disable_signals=False):
    global _node, _logger, _clock, _thread_spin
    _node = rclpy.create_node(
        node_name,
        allow_undeclared_parameters = True,
        automatically_declare_parameters_from_overrides = True,
    )
    _logger = _node.get_logger()
    _clock = _node.get_clock()

    _thread_spin = threading.Thread(target=rclpy.spin, args=(_node, ), daemon=True)
    _thread_spin.start()

def is_shutdown():
    return not rclpy.ok()

def logdebug(log_text):
    global _logger
    _logger.debug(log_text)

logdebug_once = logdebug
logdebug_throttle = lambda rate, msg: logdebug(msg)

def loginfo(log_text):
    global _logger
    _logger.info(log_text)

loginfo_once = loginfo
loginfo_throttle = lambda rate, msg: loginfo(msg)

def logwarn(log_text):
    global _logger
    _logger.warn(log_text)

logwarn_once = logwarn
logwarn_throttle = lambda rate, msg: logwarn(msg)

def logerr(log_text):
    global _logger
    _logger.error(log_text)

logerr_once = logerr
logerr_throttle = lambda rate, msg: logerr(mssg)

def logfatal(log_text):
    global _logger
    _logger.fatal(log_text)

logfatal_once = logfatal
logfatal_throttle = lambda rate, msg: logfatal(msg)

def on_shutdown(h):
    pass

def set_param(parameter_name, parameter_value):
    global _node
    if type(parameter_value) is str:
        parameter_type = rclpy.Parameter.Type.STRING
    elif type(parameter_value) is float:
        parameter_type = rclpy.Parameter.Type.DOUBLE
    elif type(parameter_value) is int:
        parameter_type = rclpy.Parameter.Type.INT
    elif type(parameter_value) is bool:
        parameter_type = rclpy.Parameter.Type.BOOL
    else:
        raise Exception("Invalid parameter value type: %s" % str(type(parameter_value)))

    param = rclpy.parameter.Parameter(
        parameter_name,
        parameter_type,
        parameter_value,
    )
    _node.set_parameters([param])

def signal_shutdown(reason):
    rclpy.shutdown()

def sleep(duration):
    time.sleep(duration) # TODO: replace with version that respects ROS time

def spin():
    global _thread_spin
    _thread_spin.join()

def wait_for_message(topic_name, topic_type):
    global _node, _wait_for_message_release
    _wait_for_message_release = False
    sub = _node.create_subscriber(topic_name, topic_type, _release_wait_for_message)
    while not _wait_for_message_release:
        time.sleep(0.1)
    _node.destroy_subscriber(sub)

def _release_wait_for_message(self, msg):
    global _wait_for_message_release
    _wait_for_message_release = True

def wait_for_service(service_name):
    global _node
    abs_service_name = os.path.join(_node.get_namespace(), service_name)
    while True:
        for service in _node.get_service_names_and_types():
            if service[0] == abs_service_name:
                break
        time.sleep(0.5)

class Publisher(object):
    def __init__(self, topic_name, topic_type, queue_size = 1):
        global _node
        self.reg_type = "pub"
        self.data_class = topic_type
        self.name = topic_name
        self.resolved_name = topic_name
        self.type = _ros2_type_to_type_name(topic_type)
        self._pub = _node.create_publisher(topic_type, topic_name, 10)
        self.get_num_connections = self._pub.get_subscription_count

    def __del__(self):
        global _node
        _node.destroy_publisher(self._pub)

    @property
    def md5sum(self): # No good ROS2 equivalent, fake it reasonably
        return hashlib.md5(str(self.type.get_fields_and_field_types()).encode("utf-8")).hexdigest()

    def publish(self, msg):
        self._pub.publish(msg)

    def unregister(self):
        global _node
        _node.destroy_publisher(self._pub)

class Subscriber(object):
    def __init__(self, topic_name, topic_type, callback, callback_args = ()):
        global _node
        self.reg_type = "sub"
        self.data_class = topic_type
        self.name = topic_name
        self.resolved_name = topic_name
        self.type = _ros2_type_to_type_name(topic_type)
        self.callback = callback
        self.callback_args = callback_args
        self._sub = _node.create_subscription(topic_type, topic_name, self.callback, 10)
        self.get_num_connections = lambda: 1 # No good ROS2 equivalent

    def __del__(self):
        global _node
        _node.destroy_subscription(self._sub)

    @property
    def md5sum(self): # No good ROS2 equivalent, fake it reasonably
        return hashlib.md5(str(self.type.get_fields_and_field_types()).encode("utf-8")).hexdigest()

    def unregister(self):
        global _node
        _node.destroy_subscription(self._sub)

class Service(object):
    def __init__(self, service_name, service_type, callback):
        global _node
        self._srv = _node.create_service(service_type, service_name, callback)

    def __del__(self):
        global _node
        _node.destroy_service(self._srv)

class ServiceProxy(object):
    def __init__(self, service_name, service_type):
        global _node
        self._client = _node.create_client(service_type, service_name)

    def __del__(self):
        global _node
        _node.destroy_client(self._client)
    
    def __call__(self, req):
        global _node
        resp = self._client.call_async(req)
        rclpy.spin_until_future_complete(_node, resp)
        return resp

class Duration(object):
    def __new__(cls, secs, nsecs = 0):
        global _node
        d = rclpy.duration.Duration(nanoseconds = secs * 1000000000 + nsecs)
        d.to_nsec = types.MethodType(lambda self: self.nanoseconds, d)
        d.to_sec = types.MethodType(lambda self: self.nanoseconds / 1e9, d)
        d.secs = secs
        d.nsecs = nsecs
        return d

    @classmethod
    def from_sec(cls, secs):
        return rclpy.duration.Duration(nanosecods = secs * 1000000000)

    @classmethod
    def from_seconds(cls, secs):
        return rclpy.duration.Duration(nanosecods = secs * 1000000000)

    @classmethod
    def is_zero(cls, d):
        return d.nanoseconds == 0

class Time(object):
    def __new__(cls, secs, nsecs = 0):
        t = rclpy.time.Time(nanoseconds = secs * 1000000000 + nsecs)
        t.to_nsec = types.MethodType(lambda self: self.nanoseconds, t)
        t.to_sec = types.MethodType(lambda self: self.nanoseconds / 1e9, t)
        t.secs = secs
        t.nsecs = nsecs
        return t

    @classmethod
    def from_sec(cls, secs):
        return rclpy.time.Time(nanosecods = secs * 1000000000)

    @classmethod
    def from_seconds(cls, secs):
        return rclpy.time.Time(nanosecods = secs * 1000000000)

    @classmethod
    def is_zero(cls, t):
        return t.nanoseconds == 0

    @classmethod
    def now(cls):
        global _clock
        t = _clock.now()
        t.to_nsec = types.MethodType(lambda self: self.nanoseconds, t)
        t.to_sec = types.MethodType(lambda self: self.nanoseconds / 1e9, t)
        t.secs = secs
        t.nsecs = nsecs
        return t

class Rate(object):
    def __init__(self, hz):
        global _node
        self._rate = _node.create_rate(hz)

    def __del__(self):
        global _node
        _node.destroy_rate(self._rate)

    def sleep(self):
        self._rate.sleep()

class Timer(object):
    def __init__(self, timer_period, callback):
        global _node
        self.callback = callback
        self._timer = _node.create_timer(timer_period, self.ros2_callback)

    def __del__(self):
        global _node
        _node.destroy_timer(self._timer)

    def ros2_callback(self):
        self.callback(TimerEvent(0, 0, 0, 0, 0)) # TODO: fill in these values

class TimerEvent(object):
    def __init__(self, last_expected, last_real, current_expected, current_real, last_duration):
        self.last_expected = last_expected
        self.last_real = last_real
        self.current_expected = current_expected
        self.current_real = current_real
        self.last_duration = last_duration

class ServiceProxy(object):
    pass

class ROSException(Exception):
    pass

class ROSException(ROSException):
    pass

class ROSInternalException(ROSException):
    pass

class ROSInterruptException(ROSException):
    pass

class ROSSerializationException(ROSException):
    pass

class ROSTimeMovedBackwardsException(ROSException):
    pass

class ServiceException(Exception):
    pass

class TransportException(Exception):
    pass

class TransportInitError(Exception):
    pass

class TransportTerminated(Exception):
    pass

def _ros2_type_to_type_name(ros2_type):
    """
    from std_msgs.msg import String # ros2
    _ros2_type_to_type_name(String) # --> "std_msgs/String"
    """
    try:
        first_dot = ros2_type.__module__.find(".")
        return ros2_type[0:first_dot] + "/" + ros2_type.__name__
    except:
        # this shouldn't happen but try harder, don't crash the robot for something silly like this
        return str(ros2_type).replace("<class '", "").replace("'>", "")
