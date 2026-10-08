import {A2uiSurface} from '@a2ui/react/v0_9';
import {useEffect, useState} from 'react';
import type {Processor} from './a2ui';

/** Renders every surface a processor currently holds. */
export function A2uiView({processor}: {processor: Processor}) {
  const read = () => Array.from(processor.model.surfacesMap.values());
  const [surfaces, setSurfaces] = useState(read);

  useEffect(() => {
    const sync = () => setSurfaces(read());
    sync();
    const created = processor.onSurfaceCreated(sync);
    const deleted = processor.onSurfaceDeleted(sync);
    return () => {
      created.unsubscribe();
      deleted.unsubscribe();
    };
  }, [processor]);

  return (
    <div className="a2ui-container">
      {surfaces.map(surface => (
        <A2uiSurface key={surface.id} surface={surface} />
      ))}
    </div>
  );
}
