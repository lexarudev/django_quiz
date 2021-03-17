/* eslint-disable no-underscore-dangle */

import { BaseSequenceBlock, BaseSequenceChild, BaseInsertionControl } from './BaseSequenceBlock';
import { escapeHtml as h } from '../../../utils/text';

/* global $ */

export class StreamBlockValidationError {
  constructor(nonBlockErrors, blockErrors) {
    this.nonBlockErrors = nonBlockErrors;
    this.blockErrors = blockErrors;
  }
}

class StreamChild extends BaseSequenceChild {
  /*
  wrapper for a block inside a StreamBlock, handling StreamBlock-specific metadata
  such as id
  */
  getState() {
    return {
      type: this.type,
      value: this.block.getState(),
      id: this.id,
    };
  }

  getValue() {
    return {
      type: this.type,
      value: this.block.getValue(),
      id: this.id,
    };
  }
}

class StreamBlockMenu extends BaseInsertionControl {
  constructor(placeholder, opts) {
    super(placeholder, opts);
    this.groupedChildBlockDefs = opts.groupedChildBlockDefs;

    const dom = $(`
      <div>
        <button data-streamblock-menu-open type="button" title="${h(opts.strings.ADD)}"
            class="c-sf-add-button c-sf-add-button--visible">
          <i aria-hidden="true">+</i>
        </button>
        <div data-streamblock-menu-outer>
          <div data-streamblock-menu-inner class="c-sf-add-panel"></div>
        </div>
      </div>
    `);
    $(placeholder).replaceWith(dom);
    this.element = dom.get(0);

    this.addButton = dom.find('[data-streamblock-menu-open]');
    this.addButton.click(() => {
      this.toggle();
    });

    this.outerContainer = dom.find('[data-streamblock-menu-outer]');
    this.innerContainer = dom.find('[data-streamblock-menu-inner]');
    this.hasRenderedMenu = false;
    this.isOpen = false;
    this.close({ animate: false });
  }

  renderMenu() {
    if (this.hasRenderedMenu) return;
    this.hasRenderedMenu = true;

    this.groupedChildBlockDefs.forEach(([group, blockDefs]) => {
      if (group) {
        const heading = $('<h4 class="c-sf-add-panel__group-title"></h4>').text(group);
        this.innerContainer.append(heading);
      }
      const grid = $('<div class="c-sf-add-panel__grid"></div>');
      this.innerContainer.append(grid);
      blockDefs.forEach(blockDef => {
        const button = $(`
          <button type="button" class="c-sf-button action-add-block-${h(blockDef.name)}">
            <span class="c-sf-button__icon">
              <i class="icon icon-${h(blockDef.meta.icon)}"></i>
            </span>
            <span class="c-sf-button__label">${h(blockDef.meta.label)}</span>
          </button>
        `);
        grid.append(button);
        button.click(() => {
          if (this.onRequestInsert) {
            this.onRequestInsert(this.index, { type: blockDef.name });
          }
          this.close({ animate: true });
        });
      });
    });
  }

  toggle() {
    if (this.isOpen) {
      this.close({ animate: true });
    } else {
      this.open({ animate: true });
    }
  }
  open(opts) {
    this.renderMenu();
    if (opts && opts.animate) {
      this.outerContainer.slideDown();
    } else {
      this.outerContainer.show();
    }
    this.addButton.addClass('c-sf-add-button--close');
    this.outerContainer.attr('aria-hidden', 'false');
    this.isOpen = true;
  }
  close(opts) {
    if (opts && opts.animate) {
      this.outerContainer.slideUp();
    } else {
      this.outerContainer.hide();
    }
    this.addButton.removeClass('c-sf-add-button--close');
    this.outerContainer.attr('aria-hidden', 'true');
    this.isOpen = false;
  }
}

export class StreamBlock extends BaseSequenceBlock {
  constructor(blockDef, placeholder, prefix, initialState, initialError) {
    this.blockDef = blockDef;
    this.type = blockDef.name;
    this.prefix = prefix;

    const dom = $(`
      <div class="c-sf-container ${h(this.blockDef.meta.classname || '')}">
        <input type="hidden" name="${h(prefix)}-count" data-streamfield-stream-count value="0">
        <div data-streamfield-stream-container></div>
      </div>
    `);
    $(placeholder).replaceWith(dom);

    if (this.blockDef.meta.helpText) {
      // help text is left unescaped as per Django conventions
      $(`
        <span>
          <div class="help">
            ${this.blockDef.meta.helpIcon}
            ${this.blockDef.meta.helpText}
          </div>
        </span>
      `).insertBefore(dom);
    }

    // StreamChild objects for the current (non-deleted) child blocks
    this.children = [];

    // Insertion control objects - there are one more of these than there are children.
    // The control at index n will insert a block at index n
    this.inserters = [];

    // Incrementing counter used to generate block prefixes, also reflected in the
    // 'count' hidden input. This count includes deleted items
    this.blockCounter = 0;
    this.countInput = dom.find('[data-streamfield-stream-count]');

    // Parent element of insert control and block elements (potentially including deleted items,
    // which are left behind as hidden elements with a '-deleted' input so that the
    // server-side form handler knows to skip it)
    this.sequenceContainer = dom.find('[data-streamfield-stream-container]');
    this.setState(initialState || []);
    this.container = dom;

    if (initialError) {
      this.setError(initialError);
    }
  }

  _createChild(blockDef, placeholder, prefix, index, id, initialState, opts) {
    return new StreamChild(blockDef, placeholder, prefix, index, id, initialState, opts);
  }

  _createInsertionControl(placeholder, opts) {
    // eslint-disable-next-line no-param-reassign
    opts.groupedChildBlockDefs = this.blockDef.groupedChildBlockDefs;
    return new StreamBlockMenu(placeholder, opts);
  }

  insert({ type, value, id }, index, opts) {
    const childBlockDef = this.blockDef.childBlockDefsByName[type];
    return this._insert(childBlockDef, value, id, index, opts);
  }

  _getChildDataForInsertion({ type }) {
    /* Called when an 'insert new block' action is triggered: given a dict of data from the insertion control,
    return the block definition and initial state to be used for the new block.
    For a StreamBlock, the dict of data consists of 'type' (the chosen block type name, as a string).
    */
    const blockDef = this.blockDef.childBlockDefsByName[type];
    const initialState = this.blockDef.initialChildStates[type];
    return [blockDef, initialState];
  }

  duplicateBlock(index) {
    const childState = this.children[index].getState();
    childState.id = null;
    this.insert(childState, index + 1, { animate: true });
    this.children[index + 1].focus();
  }

  setState(values) {
    super.setState(values);
    if (values.length === 0) {
      /* for an empty list, begin with the menu open */
      this.inserters[0].open({ animate: false });
    }
  }

  setError(errorList) {
    if (errorList.length !== 1) {
      return;
    }
    const error = errorList[0];

    // Non block errors
    const container = this.container[0];
    container.querySelectorAll(':scope > .help-block .help-critical').forEach(element => element.remove());

    if (error.nonBlockErrors.length > 0) {
      // Add a help block for each error raised
      error.nonBlockErrors.forEach(errorText => {
        const errorElement = document.createElement('p');
        errorElement.classList.add('help-block');
        errorElement.classList.add('help-critical');
        errorElement.innerText = errorText;
        container.insertBefore(errorElement, container.childNodes[0]);
      });
    }

    // Block errors
    // eslint-disable-next-line no-restricted-syntax
    for (const blockIndex in error.blockErrors) {
      if (error.blockErrors.hasOwnProperty(blockIndex)) {
        this.children[blockIndex].setError(error.blockErrors[blockIndex]);
      }
    }
  }
}

export class StreamBlockDefinition {
  constructor(name, groupedChildBlockDefs, initialChildStates, meta) {
    this.name = name;
    this.groupedChildBlockDefs = groupedChildBlockDefs;
    this.initialChildStates = initialChildStates;
    this.childBlockDefsByName = {};
    // eslint-disable-next-line no-unused-vars
    this.groupedChildBlockDefs.forEach(([group, blockDefs]) => {
      blockDefs.forEach(blockDef => {
        this.childBlockDefsByName[blockDef.name] = blockDef;
      });
    });
    this.meta = meta;
  }

  render(placeholder, prefix, initialState, initialError) {
    return new StreamBlock(this, placeholder, prefix, initialState, initialError);
  }
}
