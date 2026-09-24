import { UserProfile } from "./sample";

/** Props for the avatar component. */
export interface AvatarProps {
    user: UserProfile;
    size?: number;
}

/** Displays a user avatar. */
export function Avatar({ user, size }: AvatarProps) {
    return <img src={user.username} width={size} />;
}

export const AvatarList = ({ users }: { users: UserProfile[] }) => {
    return (
        <div>
            {users.map((u) => (
                <Avatar key={u.id} user={u} />
            ))}
        </div>
    );
};
