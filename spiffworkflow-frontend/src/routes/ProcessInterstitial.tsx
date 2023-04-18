import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchEventSource } from '@microsoft/fetch-event-source';
// @ts-ignore
import { Loading, Grid, Column } from '@carbon/react';
import { BACKEND_BASE_URL } from '../config';
import { getBasicHeaders } from '../services/HttpService';

// @ts-ignore
import InstructionsForEndUser from '../components/InstructionsForEndUser';
import ProcessBreadcrumb from '../components/ProcessBreadcrumb';
import { ProcessInstanceTask } from '../interfaces';

export default function ProcessInterstitial() {
  const [data, setData] = useState<any[]>([]);
  const [lastTask, setLastTask] = useState<any>(null);
  const [status, setStatus] = useState<string>('running');
  const params = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    fetchEventSource(
      `${BACKEND_BASE_URL}/tasks/${params.process_instance_id}`,
      {
        headers: getBasicHeaders(),
        onmessage(ev) {
          console.log(data, ev.data);
          const task = JSON.parse(ev.data);
          setData((prevData) => [...prevData, task]);
          setLastTask(task);
        },
        onclose() {
          setStatus('closed');
          console.log('Connection Closed by the Server');
        },
      }
    );
  }, []);

  useEffect(() => {
    // Added this seperate use effect so that the timer interval will be cleared if
    // we end up redirecting back to the TaskShow page.
    if (
      lastTask &&
      lastTask.can_complete &&
      ['User Task', 'Manual Task'].includes(lastTask.type)
    ) {
      const timerId = setInterval(() => {
        navigate(`/tasks/${lastTask.process_instance_id}/${lastTask.id}`);
      }, 1000);
      return () => clearInterval(timerId);
    }
    return undefined;
  }, [lastTask]);

  const processStatusImage = () => {
    if (status !== 'running') {
      setStatus(lastTask.state);
    }
    if (
      !lastTask.can_complete &&
      ['User Task', 'Manual Task'].includes(lastTask.type)
    ) {
      setStatus('LOCKED');
    }
    console.log(`Status is : ${status}}`);
    console.log('last task is : ', lastTask);
    switch (status) {
      case 'running':
        return (
          <Loading description="Active loading indicator" withOverlay={false} />
        );
      case 'WAITING':
        return <img src="/interstitial/clock.png" alt="Waiting ...." />;
      case 'COMPLETED':
        return <img src="/interstitial/checkmark.png" alt="Completed" />;
      case 'LOCKED':
        return <img src="/interstitial/lock.png" alt="Locked, Waiting on someone else." />;
      default:
        return null;
    }
  };

  const userMessage = (myTask: ProcessInstanceTask) => {
    if (
      !myTask.can_complete &&
      ['User Task', 'Manual Task'].includes(myTask.type)
    ) {
      return (
        <div>This task is assigned to another user or group to complete. </div>
      );
    }
    return <InstructionsForEndUser task={myTask} />;
  };

  if (lastTask) {
    return (
      <>
        <ProcessBreadcrumb
          hotCrumbs={[
            ['Process Groups', '/admin'],
            {
              entityToExplode: lastTask.process_model_identifier,
              entityType: 'process-model-id',
              linkLastItem: true,
            },
            [`Process Instance Id: ${lastTask.process_instance_id}`],
          ]}
        />
        <h1 style={{ display: 'inline-flex', alignItems: 'center' }}>
          {processStatusImage()}
          {lastTask.process_model_display_name}: {lastTask.process_instance_id}
        </h1>

        <Grid condensed fullWidth>
          <Column md={6} lg={8} sm={4}>
            <table className="table table-bordered">
              <tbody>
                {data &&
                  data.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <h3>{d.title}</h3>
                      </td>
                      <td>
                        <p>{userMessage(d)}</p>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </Column>
        </Grid>
      </>
    );
  }
  return null;
}
