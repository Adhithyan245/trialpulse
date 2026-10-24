Task T20-fix: one type error in the 3D tunnel.

You cannot run shell commands or use the web in this project; the reviewer builds it.
File you may edit: web/src/scenes/checkpoint/Tunnel3D.tsx only.

  src/scenes/checkpoint/Tunnel3D.tsx(242,12): error TS2322: Type 'RefObject<Mesh<...>>' is
  not assignable to type 'Ref<Group<Object3DEventMap>> | undefined'.
The ref passed at line 242 is typed as a Mesh ref but the element it is attached to is a
group (drei RoundedBox renders a Mesh, a <group> needs a Group ref). Make the ref type
match the element it is attached to (useRef<THREE.Group>(null) for a group, or
useRef<THREE.Mesh>(null) on the mesh) and update any code that reads it. When finished,
list the file you changed and stop.
