import multiprocessing, logging
from multiprocessing import Process, Pipe, Manager, Queue
from subprocess import Popen, PIPE
from Queue import PriorityQueue

import sys, time, os

import hafarm
from hafarm import utils
from hafarm import const
from hafarm.manager import RenderManager 

__plugin__version__ = 0.1

class LocalProcess(Process):
    def __init__(self, parms, status, stdout, stderr):
        super(LocalProcess, self).__init__()
        self.parms  = parms
        self.status = status
        self.stdout = stdout
        self.stderr = stderr
        self.receiver, self.pipe  = Pipe()
        self.deamon = True
        self.name   = parms['job_name']

    def run(self):
        """ Run command saved in parms.
        """
        command = self.parms['command'] 
        sp = Popen(command, shell=False, stdout=PIPE, stderr=PIPE)
        self.stdout[self.pid] = []
        while sp.poll() is None:
            self.stdout[self.pid] += ["".join(sp.stdout.readline())]
            self.status[self.pid]  = self.is_alive()
        self.stderr[self.pid]      = sp.stderr.readlines()
        self.status[self.pid]      = False

    def get_receiver(self):
        return self.receiver

    def pull(self):
        return self.receiver.recv()


class LocalScheduler(Process, RenderManager):
    def __init__(self, tasks=None, maxsize=100):
        super(LocalScheduler, self).__init__()
        self.queue   = PriorityQueue(maxsize)
        self.manager = Manager()
        self.tasks   = []
        self.status  = self.manager.dict()
        self.stdout  = self.manager.dict()
        self.stderr  = self.manager.dict()
        self.deamon  = True

        if tasks:
            self.schedule(tasks)

    def schedule(self, tasks):
        self.tasks  = tasks
        for task in tasks:
            # SGE priority spans -1024 <--> 1024
            p = 1 - ((task.parms['priority'] + 1024) / 2048.0)
            self.queue.put((p, task))

    def run(self):
        """ Spawns remote actions.
        """
        while not self.queue.empty():
            priority, task = self.queue.get()
            worker         = LocalProcess(task.parms, self.status, 
                                          self.stdout, self.stderr)
            worker.start()
            self.status[worker.pid] = True

    @property
    def register_manager(self):
        # TODO: How we could test here
        # if this is proper implementation of RenderManager?
        # calling test_connection()? or running attached unittest?
        # Do we need this at all?
        return True

    @property
    def version(self):
        return __plugin__version__ 

    def render(self, parms):
        """ This will be called by any derived class, to submit the jobs to farm. 
        Any information are to be provided in HaFarmParms class kept in self.parms
        variable.
        """
        self.parms = dict(parms)
        result = {}
        self.schedule([self])
        self.run()
        return result

    def get_queue_list(self):
        """Get list of defined queues from manager. 
        NOTE: API candidate.."""
        #TODO: get this from sge with qconf -sql
        return ('localhost',)

    def get_group_list(self):
        """Get list of defined groups from manager. 
        NOTE: API candidate.."""
        #TODO: get this from sge with qconf -shgrpl
        return ('localhost')

    def get_host_list(self):
        """Get list of defined groups from manager. 
        NOTE: API candidate.."""
        #TODO: get this from sge with qconf -shgrpl
        return ['localhost']

    def get_job_stats(self, job_name):
        return

    def test_connection(self):
        return





        