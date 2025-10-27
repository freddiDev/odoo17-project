/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class AttachmentPreviewDialog extends Component {
    static template = "account_petty_cash.AttachmentPreviewDialog";
    static components = { Dialog };
    static props = {
        title: String,
        src: String,
        close: Function,
    };
}

class AttachmentPreview extends Component {
    static template = "account_petty_cash.AttachmentPreview";
    static props = {
        ...standardFieldProps,
        fileNameField: { type: String, optional: true },
    };

    get hasPreview() {
        return Boolean(this.props.record.resId && this.props.record.data[this.props.name]);
    }

    get fileName() {
        if (this.props.fileNameField) {
            return this.props.record.data[this.props.fileNameField] || "Attachment";
        }
        return this.props.record.fields[this.props.name]?.string || "Attachment";
    }

    get previewSrc() {
                if (!this.hasPreview) {
            return "";
        }
        const { resModel, resId } = this.props.record;
        const unique = this.props.record.data.__lastUpdate;
        return url("/web/image", {
            model: resModel,
            id: resId,
            field: this.props.name,
            width: 40,
            height: 40,
            unique,
        });
    }

    get dialogSrc() {
        if (!this.hasPreview) {
            return "";
        }
        const { resModel, resId } = this.props.record;
        const unique = this.props.record.data.__lastUpdate;
        return url(`/web/image/${resModel}/${resId}/${this.props.name}`, unique ? { unique } : undefined);
    }

    openPreview(ev) {
        ev.stopPropagation();
        if (!this.hasPreview) {
            return;
        }
        this.env.services.dialog.add(AttachmentPreviewDialog, {
            title: this.fileName,
            src: this.dialogSrc,
        });
    }
}

const fieldRegistry = registry.category("fields");
fieldRegistry.add("attachment_preview", {
    component: AttachmentPreview,
    supportedTypes: ["binary"],
    extractProps: ({ attrs }) => ({
        fileNameField: attrs.filename,
    }),
});
