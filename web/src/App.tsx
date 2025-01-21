import { FC, useState } from "react";
import "./WorkersTable.css";
import { useWorkers, useWorker, Status } from "./api/arpa/v1/workers_rbt_react";

const WORKERS_INDEX_ID = "(singleton)";

const statusMapping = {
  [Status.NOT_STARTED]: "Not Started",
  [Status.IN_PROGRESS]: "In Progress",
  [Status.COMPLETED]: "Completed",
  [Status.FAILED]: "Failed",
};

// Display failed workers at the top.
const statusOrder = {
  [Status.NOT_STARTED]: 1,
  [Status.IN_PROGRESS]: 2,
  [Status.COMPLETED]: 3,
  [Status.FAILED]: 0,
};

const WorkerCompletionButton: FC<{ workerId: string }> = ({ workerId }) => {
  const { complete } = useWorker({ id: workerId });

  const [isCompleting, setIsCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    console.log("Completing worker", workerId);
    setIsCompleting(true);
    setError(null);

    try {
      await complete();
      console.log("Successfully completed", workerId);
    } catch (e) {
      setError("Error: " + e);
    } finally {
      console.log("Am now done with", workerId);
      setIsCompleting(false);
    }
  };

  return (
    <button
      className="complete-btn"
      onClick={handleClick}
      disabled={isCompleting}
    >
      {isCompleting ? "Completing..." : "Complete"}
      {error && <span className="error">{error}</span>}
    </button>
  );
};

const App = () => {
  const { useList, useIsFrozen, freeze } = useWorkers({ id: WORKERS_INDEX_ID });
  const { response: listResponse } = useList();
  const workers = listResponse?.workers || [];
  const { response: isFrozenResponse } = useIsFrozen();
  const frozen = isFrozenResponse?.frozen || false;

  const handleFreeze = async () => {
    await freeze({ frozen: !frozen });
  };

  // Sort `workers` by status (see `statusOrder`), and then by worker ID.
  workers.sort((a, b) => {
    if (statusOrder[a.status] < statusOrder[b.status]) {
      return -1;
    }
    if (statusOrder[a.status] > statusOrder[b.status]) {
      return 1;
    }
    if (a.workerId < b.workerId) {
      return -1;
    }
    if (a.workerId > b.workerId) {
      return 1;
    }
    return 0;
  });

  // Only show the first 10 workers.
  const shownWorkers = workers.slice(0, 10);
  const notShownWorkerCount = workers.length - shownWorkers.length;

  return (
    <div className="table-container">
      <h1>Worker Status</h1>
      <table className="workers-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Task Description</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {shownWorkers.map((worker, index) => (
            <tr key={index}>
              <td>{worker.workerId}</td>
              <td>{worker.taskDescription}</td>
              <td>{statusMapping[worker.status] || "Unknown"}</td>
              <td>
                {worker.status === Status.FAILED ? (
                  <WorkerCompletionButton workerId={worker.workerId} />
                ) : (
                  "--"
                )}
              </td>
            </tr>
          ))}
          {
            // Ensure the table always has exactly 10 elements; it makes the UI
            // less "jumpy".
            new Array(10 - shownWorkers.length).fill(null).map((_, index) => (
              <tr key={shownWorkers.length + index}>
                <td>--</td>
                <td>--</td>
                <td>--</td>
                <td>--</td>
              </tr>
            ))
          }
        </tbody>
      </table>
      {notShownWorkerCount > 0 && (
        <p className="not-shown-count">
          <em>{notShownWorkerCount} workers not shown</em>
        </p>
      )}
      {frozen ? (
        <button className="freeze-btn" onClick={handleFreeze}>
          Unfreeze Worker Creation
        </button>
      ) : (
        <button className="freeze-btn" onClick={handleFreeze}>
          Freeze Worker Creation
        </button>
      )}
    </div>
  );
};

export default App;
