import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';
import { AppModule } from './app/app.module';

import { provideCharts, withDefaultRegisterables } from 'ng2-charts';

platformBrowserDynamic([
  provideCharts(withDefaultRegisterables())
])
  .bootstrapModule(AppModule)
  .catch(err => console.error(err));
