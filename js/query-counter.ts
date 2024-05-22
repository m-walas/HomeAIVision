import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

class QueryCounter extends LitElement {
  @property() hass;

  render() {
    return html`
      <ha-card header="Query Counter">
        <div class="card-content">
          <p>Query counter content goes here.</p>
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host {
        display: block;
      }
      .card-content {
        padding: 16px;
      }
    `;
  }
}

if (!customElements.get('query-counter')) {
  customElements.define('query-counter', QueryCounter);
}
