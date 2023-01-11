import type { Definition } from '@hotwired/stimulus';

import { AutoFieldController } from './AutoFieldController';
import { SkipLinkController } from './SkipLinkController';
import { UpgradeController } from './UpgradeController';

/**
 * Important: Only add default core controllers that should load with the base admin JS bundle.
 */
export const coreControllerDefinitions: Definition[] = [
  { controllerConstructor: AutoFieldController, identifier: 'w-auto-field' },
  { controllerConstructor: SkipLinkController, identifier: 'w-skip-link' },
  { controllerConstructor: UpgradeController, identifier: 'w-upgrade' },
];
