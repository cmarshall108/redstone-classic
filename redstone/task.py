"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, June 11th, 2018
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import enum
import time
import threading


class TaskError(RuntimeError):
    """
    An task specific runtime error
    """

class TaskState(enum.Enum):
    """
    An enum that defines states in which a task can be in
    """

    WAITING = 0
    RUNNING = 1

class TaskResult(enum.Enum):
    """
    An enum that defines the results in which a task can return
    """

    DONE = 0
    WAIT = 1
    CONT = 2

class Task(object):
    """
    An task object is an object that keeps track of an function that
    is called in synchronous form on the task manager
    """

    def __init__(self, task_manager, name, priority, delay, function, *args, **kwargs):
        self._task_manager = task_manager
        self._name = name
        self._priority = priority

        self._delay = delay
        self._can_delay = True
        self._timestamp = self.get_timestamp()

        self._state = TaskState.WAITING
        self._last_state = None

        self._function = function
        self._args = args
        self._kwargs = kwargs

    @property
    def name(self):
        return self._name

    @property
    def priority(self):
        return self._priority

    @priority.setter
    def priority(self, priority):
        self._priority = priority

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = delay

    @property
    def can_delay(self):
        return self._can_delay

    @can_delay.setter
    def can_delay(self, can_delay):
        self._can_delay = can_delay

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._last_state = self._state
        self._state = state

    @property
    def last_state(self):
        return self._last_state

    @property
    def function(self):
        return self._function

    @property
    def args(self):
        return self._args

    @property
    def kwargs(self):
        return self._kwargs

    @property
    def done(self):
        return TaskResult.DONE

    @property
    def wait(self):
        return TaskResult.WAIT

    @property
    def cont(self):
        return TaskResult.CONT

    def __cmp__(self, other_task):
        """
        Compares our task priorty value with the other task's priorty
        value to see which has a higher priority...

        Args:
            Task: The other task instance to compare to

        Returns:
            Int: Comparison result
        """

        return cmp(self._priority, other_task.priority)

    def get_timestamp(self):
        """
        Gets the current timestamp in epoch form and rounds the integer
        decimal place...

        Args:
            None

        Returns:
            float: Timestamp value in epoch form
        """

        return round(time.time(), 2)

    def setup(self):
        """
        Sets up the current task instance, this method can be overidden
        by the user to initialize anything...

        Args:
            None

        Returns:
            None
        """

    def run(self):
        """
        Attempts to run the current task function specified by the user,
        if their is a delay set for this task and the correct amount of time
        according to the delay value has not passed, then the task will not be ran...

        Args:
            None

        Returns:
            None
        """

        if self._can_delay and self.get_timestamp() - self._timestamp < self._delay:
            return

        self.state = TaskState.RUNNING

        try:
            result = self._function(self, *self._args, **self._kwargs)
        except Exception as e:
            raise TaskError(e)

        if result == TaskResult.DONE:
            self._task_manager.remove_task(self)
        elif result == TaskResult.WAIT:
            self._can_delay = True
            self._timestamp = self.get_timestamp()
        elif result == TaskResult.CONT:
            self._can_delay = False
            self._timestamp = 0
        else:
            raise TaskError('Cannot handle invalid task result <%r>!' % (
                result))

        self.state = TaskState.WAITING

    def destroy(self):
        """
        Destroys the current task instance, sets all variables within
        the instance to nonetypes and assumes the task is removed...

        Args:
            None

        Returns:
            None
        """

        self._id = None
        self._name = None
        self._priority = 0

        self._delay = 0
        self._can_delay = False
        self._timestamp = 0

        self._function = None
        self._args = None
        self._kwargs = None

class TaskManager(object):
    """
    An task manager is an class that manages all task instances,
    this acts as a round robin scheduler for asynchronous programming
    utilizing threads...
    """

    def __init__(self):
        self._tasks = {}
        self._shutdown = False

    @property
    def tasks(self):
        return self._tasks

    @property
    def shutdown(self):
        return self._shutdown

    @shutdown.setter
    def shutdown(self, shutdown):
        self._shutdown = shutdown

    def has_task(self, task_name):
        return task_name in self._tasks

    def add_task(self, task_name, function, *args, **kwargs):
        """
        Adds a task to the dictionary of tasks so that the task manager's
        main loop or one of the task chains can execute the task...

        Args:
            String: The name of the task process
            Function: The function called by the task manager
            Args: An list of args to be called with the function
            Kwargs: An list of keyword args to be called with the function

        Returns:
            Task: The newly created task instance
        """

        if self.has_task(task_name):
            raise TaskError('Failed to add an already existing task <%s>!' % (
                task_name))

        priority = kwargs.pop('priority', 0)
        delay = kwargs.pop('delay', 0)

        task = Task(self, task_name, priority, delay,
            function, *args, **kwargs)

        self._tasks[task_name] = task
        task.setup()

        return task

    def remove_task(self, task):
        """
        Removes a task from the dictionary of tasks so that the task manager
        will no longer execute the task, this also calls "destroy" on the
        task instance to remove it's references from memory...

        Args:
            Task: The task instance to be removed

        Returns:
            None
        """

        if not self.has_task(task.name):
            raise TaskError('Failed to remove an non-existant task <%s>!' % (
                task.name))

        task.destroy()
        del self._tasks[task.name]

    def get_task(self, task_name):
        """
        Attempts to retrieve a task instance by it's name specified...

        Args:
            String: The name of the task to retrieve

        Returns:
            Task: The task instance which is referenced by it's name
        """

        return self._tasks.get(task_name)

    def setup(self):
        """
        Sets up the task manager instance, this method can be overidden
        by the user to initialize anything...

        Args:
            None

        Returns:
            None
        """

    def __update(self):
        """
        Called by the task manager's main loop, this sorts the task instances by
        priority and then runs each task until it is complete...

        Args:
            None

        Returns:
            None
        """

        pending_tasks = sorted([task for task in self._tasks.values() \
            if task.state == TaskState.WAITING])

        for task in pending_tasks:
            task.run()

    def run(self):
        """
        This is the task manager's main loop which is also the applications
        mainloop, every event in the application is ran by the task manager here...

        Args:
            None

        Returns:
            None
        """

        def mainloop():
            self.setup()

            while not self._shutdown:
                try:
                    self.__update()
                except (KeyboardInterrupt, SystemExit):
                    self._shutdown = True

                time.sleep(0.01)

            self.destroy()

        thread = threading.Thread(target=mainloop)
        thread.daemon = True
        thread.start()

    def destroy(self):
        """
        Destroys the current task manager instance, assuming
        the application is shutting down...

        Args:
            None

        Returns:
            None
        """

        self._tasks = {}
