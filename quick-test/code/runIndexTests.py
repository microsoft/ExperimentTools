# runIndexTests.py: test out the mongo "get_next_child_run()" API
import time
import random
from threading import Thread

from xtlib import utils
from xtlib import constants
from xtlib.helpers import xt_config
from xtlib.storage.store import Store
from xtlib.storage.mongo_run_index import MongoRunIndex, build_active_runs

# status values
constants.WAITING = "waiting_for_restart"
constants.STARTED = "started"
constants.RESTARTED = "restarted"
constants.UNSTARTED = "unstarted"
constants.COMPLETED = "completed"

class RunIndexTester():
    def __init__(self, mongo):
        '''
        unit test for mongo api: get_next_child_run().  we test on top of an 
        existing job in the current storage system:
            - job7569: 5 nodes, 10 child runs each, runs 4603-4607
        '''
        self.mongo = mongo

        self.job_id = "job7569"
        self.parent_run_name = "run9999"   # not a real run
        self.node_count = 3
        self.run_count = 15
        self.schedule = "static"
        self.assert_count = 0

    def _assert(self, value):
        assert value
        self.assert_count  += 1

    def reset_active_runs(self, schedule):
        # rewrite an initial set of active_runs for the job
        entries = build_active_runs(schedule, self.run_count, self.node_count)

        self.mongo.mongo_db["__jobs__"].find_and_modify({"job_id": self.job_id} , update={"$set": {"schedule": schedule}}, new=True)
        
        entries_with_job_id = [ ]
        for entry in entries:
            entry['job_id'] = self.job_id
            entries_with_job_id.append(entry)

        self.mongo.mongo_db["__active_runs__"].insert_many(entries_with_job_id)
        
        #print("fresh active_runs: ", ar["active_runs"])

    def ar_status_check(self, status):
        active_runs = self.mongo.mongo_db["__active_runs__"].find( {"job_id": self.job_id} )        active_runs = utils.safe_cursor_value(cursor, "active_runs")

        for ar in active_runs:
            ar_status = utils.safe_cursor_value(ar, "status")
            self._assert(ar_status == status)

    def run_sequential_tests(self, schedule):
        print("runIndexTests: run_sequential_tests, schedule={}".format(schedule))

        self.reset_active_runs(schedule)
        self.ar_status_check(constants.UNSTARTED)

        entries_by_node = {}

        print("  starting runs")
        for node_index in range(self.node_count):
            node_id = "node" + str(node_index)
            mri = MongoRunIndex(self.mongo, self.job_id, self.parent_run_name, node_id)
            entries = []

            while True:
                entry = mri.get_next_child_run()
                if not entry:
                    break
                #print("entry: ", entry)

                run_index = entry["run_index"]
                node_id = entry["node_id"] 
                run_name = entry["run_name"] 
                status = entry["status"] 

                # testing
                self._assert( self.parent_run_name+"." in run_name )
                self._assert( status == "started" )
                self._assert( node_id == node_id )

                entries.append(entry)

            if schedule == "static":
                runs_per_node = self.run_count / self.node_count
                self._assert( len(entries) == runs_per_node )
            else:
                if node_id == "node0":
                    self._assert( len(entries) == self.run_count )
                else:
                    self._assert( len(entries) == 0)

            entries_by_node[node_id] = entries

        self.ar_status_check(constants.STARTED)

        print("  completing runs")

        for node_index in range(self.node_count):
            node_id = "node" + str(node_index)

            for entry in entries_by_node[node_id]:
                mri.mark_child_run_completed(entry)

        self.ar_status_check(constants.COMPLETED)

        return self.assert_count

    def run_random_tests(self, schedule, restart_nodes):
        print("runIndexTests: run_random_tests, schedule={}, restart={}".format(schedule, restart_nodes))

        self.reset_active_runs(schedule)
        self.ar_status_check(constants.UNSTARTED)

        print("  starting runs")
        runs_per_node = self.run_count // self.node_count
        node_runners = []

        for node_index in range(self.node_count):
            node_id = "node" + str(node_index)
            node_runner = NodeRunner(self.mongo, self.job_id, self.parent_run_name, node_id, runs_per_node, self)
            node_runner.start()

            node_runners.append(node_runner)

        if restart_nodes:
            
            time.sleep(3)

            for _ in range(3):
                # pick node at random
                node_index = random.randrange(0, self.node_count-1)
                nr = node_runners[node_index]

                # restart node
                nr.restart()

                time.sleep(1)

        # wait for all threads to complete
        for nr in node_runners:
            nr.wait_for_all_threads()
                
        self.ar_status_check(constants.COMPLETED)

    def test_schedule(self, schedule):
        self.run_sequential_tests(schedule)
        self.run_random_tests(schedule, False)
        self.run_random_tests(schedule, True)

class NodeRunner():
    def __init__(self, mongo, job_id, parent_run_name, node_id, run_count, tester):
        self.mongo = mongo
        self.job_id = job_id
        self.parent_run_name = parent_run_name
        self.node_id = node_id
        self.run_count = run_count
        self.tester = tester

        self.threads = []
        self.restarting = False

    def start(self):
        self.start_core()

    def restart(self):
        print("  RESTARTING: " + self.node_id)

        # stop in running threads
        self.restarting = True
        self.wait_for_all_threads()
        self.restarting = False

        self.start_core(is_restart=True)

    def start_core(self, is_restart=False):
        self.mri = MongoRunIndex(self.mongo, self.job_id, self.parent_run_name, self.node_id)
        self.threads = []

        if is_restart:
            self.restart_status_check()

        # start threads
        for i in range(self.run_count):
            run_worker = Thread(target=self.runner, args=(self.mri,))
            run_worker.start()

            self.threads.append(run_worker)

    def restart_status_check(self):
        active_runs = self.mongo.mongo_db["__active_runs__"].find( {"job_id": self.job_id} )

        for ar in active_runs:
            node_id = utils.safe_cursor_value(ar, "node_id")
            if node_id == self.node_id:
                ar_status = utils.safe_cursor_value(ar, "status")
                self.tester._assert( ar_status in [constants.UNSTARTED, constants.WAITING, constants.COMPLETED] )

    def wait_for_all_threads(self):
        for thread in self.threads:
            thread.join()

    def runner(self, mri):
        if self.restarting:
            return

        sleep_time = 3 * random.random()
        time.sleep(sleep_time)

        if self.restarting:
            return

        entry = mri.get_next_child_run()
        if entry:
            print("  starting: " + str(entry))

            status = entry["status"]
            self.tester._assert( status in [constants.STARTED, constants.RESTARTED] )

            if self.restarting:
                return

            run_time = 6 * random.random()
            time.sleep(run_time)

            if self.restarting:
                return

            print("  completing: " + str(entry))
            mri.mark_child_run_completed(entry)

def main():
    config = xt_config.get_merged_config()
    store = Store(config=config)
    
    tester = RunIndexTester(store.mongo)
    
    tester.test_schedule("static")
    tester.test_schedule("dynamic")

    count = tester.assert_count
    return count

if __name__ == "__main__":
    main()