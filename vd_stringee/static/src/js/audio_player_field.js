/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Inline audio player for a Char field that holds a URL.
 * Usage in XML: <field name="recording_player_url" widget="audio_player"/>
 */
export class AudioPlayerField extends Component {
    static template = "vd_stringee.AudioPlayerField";
    static props = { ...standardFieldProps };

    get url() {
        return this.props.record.data[this.props.name] || "";
    }
}

registry.category("fields").add("audio_player", {
    component: AudioPlayerField,
    supportedTypes: ["char"],
});
