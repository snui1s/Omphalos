package main

type Account struct {
    ID      string
    Balance float64
}

type BankService interface {
    Transfer(from, to string, amount float64) error
}

func OpenAccount(id string) *Account {
    return &Account{ID: id, Balance: 0}
}

func (a *Account) Deposit(amount float64) {
    a.Balance += amount
}
