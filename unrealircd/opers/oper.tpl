oper LOGIN {
	class           opers;
	from {
		userhost USER@HOST;
	};

	password "PASSWORD HASH" { HASHMETHOD; };

	flags {
		netadmin;
		can_zline;
		can_gzline;
		can_gkline;
		can_override;
		global;
	};
};
