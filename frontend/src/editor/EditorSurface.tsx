import { Editor } from "@tiptap/core";
import Image from "@tiptap/extension-image";
import { Placeholder } from "@tiptap/extensions";
import StarterKit from "@tiptap/starter-kit";
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconBlockquote,
  IconBold,
  IconCode,
  IconH1,
  IconH2,
  IconH3,
  IconItalic,
  IconLink,
  IconList,
  IconListNumbers,
  IconMinus,
  IconPhotoPlus,
  IconStrikethrough,
  IconUnderline,
} from "@tabler/icons-react";
import {
  useEffect,
  useReducer,
  useRef,
  useState,
  type ChangeEvent,
  type ReactNode,
} from "react";

import { Button, Field, Input, Modal } from "../components/ui";

const EMPTY_DOC = {
  type: "doc",
  content: [{ type: "paragraph" }],
};

function ToolButton({
  label,
  active = false,
  disabled = false,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className={`tool-button ${active ? "active" : ""}`.trim()}
      aria-label={label}
      title={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function EditorSurface({
  initialContent,
  canEdit,
  saving,
  onSave,
  onChange,
  onDirtyChange,
  onUploadImage,
}: {
  initialContent: unknown;
  canEdit: boolean;
  saving: boolean;
  onSave: (json: unknown) => void;
  onChange?: (json: unknown) => void;
  onDirtyChange: (dirty: boolean) => void;
  onUploadImage: (file: File) => Promise<string | null>;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const saveRef = useRef(onSave);
  const changeRef = useRef(onChange);
  const dirtyRef = useRef(onDirtyChange);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [linkValue, setLinkValue] = useState("");
  const [uploading, setUploading] = useState(false);
  const [, forceRender] = useReducer((value: number) => value + 1, 0);

  useEffect(() => {
    saveRef.current = onSave;
    changeRef.current = onChange;
    dirtyRef.current = onDirtyChange;
  }, [onSave, onChange, onDirtyChange]);

  useEffect(() => {
    if (!hostRef.current) return;
    const instance = new Editor({
      element: hostRef.current,
      editable: canEdit,
      extensions: [
        StarterKit.configure({
          heading: { levels: [1, 2, 3, 4] },
          link: {
            openOnClick: false,
            autolink: true,
            defaultProtocol: "https",
          },
        }),
        Image.configure({
          inline: false,
          allowBase64: false,
          HTMLAttributes: { class: "editor-image" },
        }),
        Placeholder.configure({
          placeholder: canEdit
            ? "Start writing, or import an RST/MyST file…"
            : "This page has no content yet.",
        }),
      ],
      content: (initialContent as never) ?? EMPTY_DOC,
      editorProps: {
        attributes: {
          class: "tiptap",
          "aria-label": "Document body",
        },
        handleKeyDown: (_view, event) => {
          if (
            (event.metaKey || event.ctrlKey) &&
            event.key.toLowerCase() === "s"
          ) {
            event.preventDefault();
            saveRef.current(instance.getJSON());
            return true;
          }
          return false;
        },
      },
      onUpdate: ({ editor: current }) => {
        dirtyRef.current(true);
        changeRef.current?.(current.getJSON());
      },
    });
    setEditor(instance);
    return () => {
      instance.destroy();
      setEditor(null);
    };
  }, [canEdit]);

  useEffect(() => {
    if (!editor) return;
    const update = () => forceRender();
    editor.on("transaction", update);
    editor.on("selectionUpdate", update);
    return () => {
      editor.off("transaction", update);
      editor.off("selectionUpdate", update);
    };
  }, [editor]);

  const upload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !editor) return;
    setUploading(true);
    try {
      const blobUrl = await onUploadImage(file);
      if (blobUrl) {
        editor.chain().focus().setImage({ src: blobUrl, alt: file.name }).run();
      }
    } finally {
      setUploading(false);
    }
  };

  const openLink = () => {
    if (!editor) return;
    setLinkValue(String(editor.getAttributes("link").href ?? ""));
    setLinkOpen(true);
  };

  const applyLink = () => {
    if (!editor) return;
    const href = linkValue.trim();
    if (href) {
      editor.chain().focus().extendMarkRange("link").setLink({ href }).run();
    } else {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
    }
    setLinkOpen(false);
  };

  const headingLevel = editor?.isActive("heading", { level: 1 })
    ? "1"
    : editor?.isActive("heading", { level: 2 })
      ? "2"
      : editor?.isActive("heading", { level: 3 })
        ? "3"
        : "";

  return (
    <div className="editor-shell">
      {canEdit && editor ? (
        <div className="editor-toolbar" role="toolbar" aria-label="Formatting">
          <div className="tool-group">
            <select
              className="tool-select"
              aria-label="Text style"
              value={headingLevel}
              onChange={(event) => {
                const value = event.target.value;
                if (!value) {
                  editor.chain().focus().setParagraph().run();
                } else {
                  editor
                    .chain()
                    .focus()
                    .toggleHeading({
                      level: Number(value) as 1 | 2 | 3,
                    })
                    .run();
                }
              }}
            >
              <option value="">Paragraph</option>
              <option value="1">Heading 1</option>
              <option value="2">Heading 2</option>
              <option value="3">Heading 3</option>
            </select>
          </div>
          <div className="tool-group">
            <ToolButton
              label="Bold"
              active={editor.isActive("bold")}
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <IconBold size={17} />
            </ToolButton>
            <ToolButton
              label="Italic"
              active={editor.isActive("italic")}
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <IconItalic size={17} />
            </ToolButton>
            <ToolButton
              label="Underline"
              active={editor.isActive("underline")}
              onClick={() => editor.chain().focus().toggleUnderline().run()}
            >
              <IconUnderline size={17} />
            </ToolButton>
            <ToolButton
              label="Strikethrough"
              active={editor.isActive("strike")}
              onClick={() => editor.chain().focus().toggleStrike().run()}
            >
              <IconStrikethrough size={17} />
            </ToolButton>
            <ToolButton
              label="Inline code"
              active={editor.isActive("code")}
              onClick={() => editor.chain().focus().toggleCode().run()}
            >
              <IconCode size={17} />
            </ToolButton>
          </div>
          <div className="tool-group">
            <ToolButton
              label="Heading 1"
              active={editor.isActive("heading", { level: 1 })}
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 1 }).run()
              }
            >
              <IconH1 size={18} />
            </ToolButton>
            <ToolButton
              label="Heading 2"
              active={editor.isActive("heading", { level: 2 })}
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 2 }).run()
              }
            >
              <IconH2 size={18} />
            </ToolButton>
            <ToolButton
              label="Heading 3"
              active={editor.isActive("heading", { level: 3 })}
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 3 }).run()
              }
            >
              <IconH3 size={18} />
            </ToolButton>
          </div>
          <div className="tool-group">
            <ToolButton
              label="Bullet list"
              active={editor.isActive("bulletList")}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
              <IconList size={17} />
            </ToolButton>
            <ToolButton
              label="Numbered list"
              active={editor.isActive("orderedList")}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
              <IconListNumbers size={17} />
            </ToolButton>
            <ToolButton
              label="Block quote"
              active={editor.isActive("blockquote")}
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
            >
              <IconBlockquote size={17} />
            </ToolButton>
            <ToolButton
              label="Code block"
              active={editor.isActive("codeBlock")}
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
            >
              <IconCode size={17} />
            </ToolButton>
            <ToolButton
              label="Horizontal rule"
              onClick={() => editor.chain().focus().setHorizontalRule().run()}
            >
              <IconMinus size={17} />
            </ToolButton>
          </div>
          <div className="tool-group">
            <ToolButton
              label="Link"
              active={editor.isActive("link")}
              onClick={openLink}
            >
              <IconLink size={17} />
            </ToolButton>
            <ToolButton
              label={uploading ? "Uploading image…" : "Insert image"}
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              <IconPhotoPlus size={17} />
            </ToolButton>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp,image/avif"
              hidden
              onChange={upload}
            />
          </div>
          <div className="tool-group tool-group-end">
            <ToolButton
              label="Undo"
              disabled={!editor.can().undo()}
              onClick={() => editor.chain().focus().undo().run()}
            >
              <IconArrowBackUp size={17} />
            </ToolButton>
            <ToolButton
              label="Redo"
              disabled={!editor.can().redo()}
              onClick={() => editor.chain().focus().redo().run()}
            >
              <IconArrowForwardUp size={17} />
            </ToolButton>
          </div>
        </div>
      ) : null}

      <div className="editor-scroll">
        <div className="editor-page">
          <div ref={hostRef} />
        </div>
      </div>

      {saving ? <div className="editor-saving">Saving…</div> : null}

      <Modal open={linkOpen} onOpenChange={setLinkOpen} title="Link">
        <Field label="URL" hint="Leave empty to remove the link.">
          <Input
            autoFocus
            value={linkValue}
            placeholder="https://example.com"
            onChange={(event) => setLinkValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                applyLink();
              }
            }}
          />
        </Field>
        <div className="dialog-actions">
          <Button onClick={() => setLinkOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={applyLink}>
            Apply link
          </Button>
        </div>
      </Modal>
    </div>
  );
}
