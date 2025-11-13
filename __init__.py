import bpy
from bpy.types import Panel, Operator, PropertyGroup, AddonPreferences

def get_collections():
    """Return all top-level collections of the active scene."""
    return list(bpy.context.scene.collection.children)

def get_layer_collections(context):
    """Return all top-level Layer Collections of the active view layer."""
    # We must use context.view_layer if available for proper context
    return list(context.view_layer.layer_collection.children)

def toggle_viewport_all():
    """Toggles viewport visibility for all top-level collections (Hide All or Show All)."""
    context = bpy.context
    layer_cols = get_layer_collections(context)
    
    # Check current state based on Layer Collections
    any_hidden = any(lc.hide_viewport for lc in layer_cols)
    new_state = not any_hidden
    
    # Iterate and synchronize both Layer Collection (lc) and Data Block Collection (col)
    for lc in layer_cols:
        lc.hide_viewport = new_state
        # Also set the Data Block Collection property for full synchronization
        if lc.collection:
            lc.collection.hide_viewport = new_state
        
def toggle_render_all():
    """Toggles render visibility for all top-level collections (Hide All or Show All)."""
    # Render visibility is already on the Data Block, so no change needed here.
    cols = get_collections()
    any_hidden = any(col.hide_render for col in cols)
    for col in cols:
        col.hide_render = not any_hidden
        
class COLLECTION_SET_ACTIVE_OT_set(bpy.types.Operator):
    """Sets the indexed collection as the active collection."""
    bl_idname = "view3d.collection_set_active"
    bl_label = "Set Active Collection"
    bl_options = {'REGISTER'}

    key: bpy.props.StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        # Only run if the specific preference is enabled
        if not prefs.enable_active:
            return {'CANCELLED'}

        k = self.key
        cols = get_collections()

        if k.isdigit():
            index = int(k)
            if index == 0:
                index = 10
            
            if 1 <= index <= len(cols):
                col = cols[index - 1]
                # Set the current scene's active layer (collection)
                context.view_layer.active_layer_collection = context.view_layer.layer_collection.children[col.name]
                return {'FINISHED'}
                
        return {'CANCELLED'}

class COLLECTION_TOGGLE_OT_toggle(bpy.types.Operator):
    """Handle 1–0, Shift+1–0, and ~ for collection visibility."""
    bl_idname = "view3d.collection_toggle"
    bl_label = "Collection Toggle"
    bl_options = {'REGISTER', 'UNDO'}

    key: bpy.props.StringProperty()
    shift_pressed: bpy.props.BoolProperty(default=False)
    alt_pressed: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        k = self.key
        cols = get_collections()

        alt_action_taken = False
        action_performed = False 

        if k.isdigit():
            index = int(k)
            if index == 0:
                index = 10
            
            if 1 <= index <= len(cols):
                col = cols[index - 1]
                
                # Get the corresponding Layer Collection for viewport actions
                lc = context.view_layer.layer_collection.children.get(col.name)
                if not lc:
                    return {'CANCELLED'}

                # --- ALT PRESSED: Render Toggle/Isolate (Primary Action) ---
                if self.alt_pressed:
                    if prefs.enable_render:
                        if self.shift_pressed:
                            # ALT + SHIFT: TOGGLE RENDER
                            col.hide_render = not col.hide_render
                        else:
                            # ALT + 1-0: ISOLATE RENDER
                            for c in cols:
                                c.hide_render = (c != col)
                        
                        alt_action_taken = True
                        action_performed = True
                    else:
                        return {'CANCELLED'}

                # --- NO ALT PRESSED: Viewport Toggle/Isolate ---
                else:
                    if self.shift_pressed:
                        # SHIFT + 1-0: TOGGLE VIEWPORT (Forced synchronization)
                        if prefs.enable_view:
                            new_state = not lc.hide_viewport
                            lc.hide_viewport = new_state
                            col.hide_viewport = new_state
                            action_performed = True
                        else:
                            return {'CANCELLED'}
                        
                    else:
                        # Set Active Collection
                        if prefs.enable_active:
                            # Set the current scene's active layer (collection)
                            context.view_layer.active_layer_collection = lc
                            action_performed = True
                        
                        # 1-0 KEYPRESS: ISOLATE VIEWPORT (Forced synchronization)
                        if prefs.enable_view:
                            isolate_lc = lc
                            all_layer_cols = context.view_layer.layer_collection.children
                            
                            for child_lc in all_layer_cols:
                                is_target = (child_lc == isolate_lc)
                                
                                # Set Layer Collection visibility
                                child_lc.hide_viewport = not is_target
                                
                                # Set Data Block Collection visibility for synchronization
                                if child_lc.collection:
                                    child_lc.collection.hide_viewport = not is_target

                            action_performed = True
                        else:
                            # If no action is taken, we must cancel. The set_active operator handles the other case.
                            return {'CANCELLED'}
                        

        elif k == 'ACCENT_GRAVE':
            if self.alt_pressed:
                if prefs.enable_render:
                    toggle_render_all() 
                    alt_action_taken = True
                    action_performed = True
            else:
                if prefs.enable_view:
                    toggle_viewport_all() # Uses the updated sync function
                    action_performed = True

        if alt_action_taken:
            self.alt_pressed = False
            
        if action_performed:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

addon_keymaps = []

def register_keymaps():
    prefs = bpy.context.preferences.addons[__name__].preferences
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    # Keymap for the 3D Viewport
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')

    key_defs = [
        ('ONE', '1'), ('TWO', '2'), ('THREE', '3'), ('FOUR', '4'),
        ('FIVE', '5'), ('SIX', '6'), ('SEVEN', '7'),
        ('EIGHT', '8'), ('NINE', '9'), ('ZERO', '0')
    ]

    items = []

    for key_code, char in key_defs:
        # Set Active Collection
        kmi_active = km.keymap_items.new(COLLECTION_SET_ACTIVE_OT_set.bl_idname, key_code, 'PRESS', repeat=False)
        kmi_active.properties.key = char
        items.append(kmi_active)

        # --- Viewport keys (enable_view) ---
        if prefs.enable_view:
            # 1-0: Isolate Collection
            kmi = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, key_code, 'PRESS', repeat=False)
            kmi.properties.key = char
            kmi.properties.shift_pressed = False
            kmi.properties.alt_pressed = False
            items.append(kmi)

            # Shift+1-0: Toggle Viewport
            kmi_shift = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, key_code, 'PRESS', shift=True, repeat=False)
            kmi_shift.properties.key = char
            kmi_shift.properties.shift_pressed = True
            kmi_shift.properties.alt_pressed = False
            items.append(kmi_shift)

        # --- Render keys (enable_render) ---
        if prefs.enable_render:
            # Alt+1-0: Isolate Render
            kmi_alt = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, key_code, 'PRESS', alt=True, repeat=False)
            kmi_alt.properties.key = char
            kmi_alt.properties.shift_pressed = False 
            kmi_alt.properties.alt_pressed = True
            items.append(kmi_alt)
            
            # Alt+Shift+1-0: Toggle Render 
            kmi_shift_alt = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, key_code, 'PRESS', alt=True, shift=True, repeat=False)
            kmi_shift_alt.properties.key = char
            kmi_shift_alt.properties.shift_pressed = True 
            kmi_shift_alt.properties.alt_pressed = True
            items.append(kmi_shift_alt)


    # --- Tilde keys ---
    if prefs.enable_view:
        # Tilde: Toggle All Viewport
        kmi_tilde = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, 'ACCENT_GRAVE', 'PRESS', repeat=False)
        kmi_tilde.properties.key = 'ACCENT_GRAVE'
        items.append(kmi_tilde)

    if prefs.enable_render:
        # Alt+Tilde: Toggle Render All
        kmi_alt_tilde = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, 'ACCENT_GRAVE', 'PRESS', alt=True, repeat=False)
        kmi_alt_tilde.properties.key = 'ACCENT_GRAVE'
        kmi_alt_tilde.properties.alt_pressed = True
        items.append(kmi_alt_tilde)
        
        # Alt+Shift+Tilde: Toggle Render All
        kmi_shift_alt_tilde = km.keymap_items.new(COLLECTION_TOGGLE_OT_toggle.bl_idname, 'ACCENT_GRAVE', 'PRESS', alt=True, shift=True, repeat=False)
        kmi_shift_alt_tilde.properties.key = 'ACCENT_GRAVE'
        kmi_shift_alt_tilde.properties.alt_pressed = True
        kmi_shift_alt_tilde.properties.shift_pressed = True
        items.append(kmi_shift_alt_tilde)

    addon_keymaps.append((km, items))

def unregister_keymaps():
    for km, items in addon_keymaps:
        for kmi in items:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()

# --- Addon Preferences ---
class COLLECTION_TOGGLE_Preferences(AddonPreferences):
    bl_idname = __name__
    
    def update_keymaps(self, context):
        unregister_keymaps()
        register_keymaps()
        
    enable_view: bpy.props.BoolProperty(
        name="Toggle view",
        description="Show/hide collections with keyboard",
        default=True,
        update=lambda self, context: self.update_keymaps(context)
    )
    enable_render: bpy.props.BoolProperty(
        name="Toggle render",
        description="Disable in render with ALT + 1-0",
        default=True,
        update=lambda self, context: self.update_keymaps(context)
    )
    enable_active: bpy.props.BoolProperty(
        name="Activate collection",
        description="Also select collection with keyboard",
        default=True
    )
    show_info: bpy.props.BoolProperty(
        name="Show info",
        description="Show information boxes",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Show/hide collections with keyboard 1-0")
        row = layout.row()
        row.alignment = 'LEFT'
        icon = "CHECKBOX_HLT" if self.enable_view else "CHECKBOX_DEHLT"
        txt = "Enabled" if self.enable_view else "Disabled"
        row.prop(self, "enable_view", text=txt, icon=icon)
                
        layout.label(text="Enable/disable in render with ALT + 1-0")
        icon2 = "RESTRICT_RENDER_OFF" if self.enable_render else "RESTRICT_RENDER_ON"
        txt2 = "Enabled" if self.enable_render else "Disabled"
        row = layout.row()
        row.alignment = 'LEFT'
        row.prop(self, "enable_render", text=txt2, icon=icon2)
                
        layout.label(text="Activate collection with keyboard 1-0")
        icon3 = "RESTRICT_SELECT_OFF" if self.enable_active else "RESTRICT_SELECT_ON"
        txt3 = "Enabled" if self.enable_active else "Disabled"
        row = layout.row()
        row.alignment = 'LEFT'
        row.prop(self, "enable_active", text=txt3, icon=icon3)
        
        layout.label(text="Show/hide info boxes")
        icon4 = "INFO" if self.show_info else "INFO"
        txt4 = "Enabled" if self.show_info else "Disabled"
        row = layout.row()
        row.alignment = 'LEFT'
        row.prop(self, "show_info", text=txt4, icon=icon4)

# --- UI Panel
class COLLECTION_TOGGLE_PT_ui(Panel):
    bl_label = "Collection Toggle"
    bl_idname = "COLLECTION_TOGGLE_PT_ui"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Collection Toggle'
    def draw(self, context):
        prefs = context.preferences.addons[__name__].preferences
        layout = self.layout
        
        # Viewport
        layout.label(text="Show/hide collections with keyboard 1-0")
        icon = "HIDE_OFF" if prefs.enable_view else "HIDE_ON"
        layout.prop(prefs, "enable_view", text="Toggle view", icon=icon)
        
        if prefs.show_info:
            box = layout.box()
            col = box.column()
            col.label(text="Press 1-0 on your keyboard", icon="DOT")
            col.label(text="to only see that collection.", icon="BLANK1")
            box.label(text="Hold SHIFT to toggle visibility.", icon="DOT")
            box.label(text="Press ~ to show all.", icon="DOT")
        
        layout.separator()
        
        # Render
        layout.label(text="Enable/disable in render with ALT + 1-0")
        icon2 = "RESTRICT_RENDER_OFF" if prefs.enable_render else "RESTRICT_RENDER_ON"
        layout.prop(prefs, "enable_render", text="Toggle render", icon=icon2)
        
        if prefs.show_info:
            box = layout.box()
            col = box.column()
            col.label(text="Press ALT + 1-0 on your keyboard", icon="DOT")
            col.label(text="to only render that collection.", icon="BLANK1")
            box.label(text="Hold ALT SHIFT to toggle render.", icon="DOT")
            box.label(text="Press ALT ~ to render all.", icon="DOT")
        
        layout.separator()
        
        # Active
        layout.label(text="Activate collection with keyboard 1-0")
        icon3 = "RESTRICT_SELECT_OFF" if prefs.enable_active else "RESTRICT_SELECT_ON"
        layout.prop(prefs, "enable_active", text="Toggle select", icon=icon3)
        
        layout.separator()
        
        # Info
        txt4 = "Hide info" if prefs.show_info else "Show info"
        row = layout.row()
        row.alignment = "LEFT"
        row.prop(prefs, "show_info", text=txt4, icon="INFO")

classes = [
    COLLECTION_SET_ACTIVE_OT_set,
    COLLECTION_TOGGLE_OT_toggle,
    COLLECTION_TOGGLE_Preferences,
    COLLECTION_TOGGLE_PT_ui
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_keymaps()

def unregister():
    unregister_keymaps()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
